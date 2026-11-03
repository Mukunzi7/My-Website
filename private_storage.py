"""Server-only client for a private Supabase Storage bucket.

No browser receives the secret key or an object URL. 70Scholar checks its own
session/project permissions before proxying an object through this client. The
bucket must stay private and must not have public or overly broad RLS policies.
"""
from __future__ import annotations
import json
import re
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit


class StorageError(RuntimeError):
    """Generic provider failure; never include keys, URLs or response bodies."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward server credentials to a redirect target.


class PrivateBucket:
    def __init__(self, project_url: str, secret_key: str, bucket: str):
        try:
            parsed = urlsplit(project_url.strip().rstrip('/'))
            valid_url = (parsed.scheme == 'https' and not parsed.username and not parsed.password and not parsed.port
                         and not parsed.path and not parsed.query and not parsed.fragment
                         and re.fullmatch(r'[a-z0-9-]+\.supabase\.co', parsed.hostname or ''))
        except (AttributeError, ValueError):
            valid_url = False
        if not valid_url:
            raise StorageError('Use the standard HTTPS Supabase project URL.')
        if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{1,62}', bucket or ''):
            raise StorageError('Invalid private storage bucket name.')
        if not (secret_key.startswith('sb_secret_') or
                (secret_key.startswith('eyJ') and secret_key.count('.') == 2)):
            raise StorageError('A server-only Supabase secret key is required.')
        if any(c.isspace() for c in secret_key):
            raise StorageError('Invalid storage credential.')
        self._base = 'https://' + parsed.hostname + '/storage/v1/'
        self._secret = secret_key
        self.bucket = bucket
        self._opener = urllib.request.build_opener(_NoRedirect())

    def _headers(self):
        # New sb_secret_ values are API keys, not JWTs. Supabase's gateway maps
        # them from apikey; sending them as bearer tokens causes Invalid JWT.
        headers = {'apikey': self._secret}
        if not self._secret.startswith('sb_secret_'):
            headers['Authorization'] = 'Bearer ' + self._secret
        return headers

    @staticmethod
    def _key(key: str) -> str:
        if not re.fullmatch(r'[A-Za-z0-9._/-]{1,300}', key or ''):
            raise StorageError('Invalid object key.')
        if any(part in ('', '.', '..') for part in key.split('/')):
            raise StorageError('Invalid object key.')
        return quote(key, safe='/')

    def _request(self, method, path, data=None, content_type=None, max_bytes=64 * 1024):
        headers = self._headers()
        if content_type: headers['Content-Type'] = content_type
        if method == 'POST': headers['x-upsert'] = 'false'
        req = urllib.request.Request(self._base + path, data=data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=45) as response:
                payload = response.read(max_bytes + 1)
                if len(payload) > max_bytes:
                    raise StorageError('Storage response exceeded the allowed size.')
                return payload
        except urllib.error.HTTPError as exc:
            # Retain only the numeric status and a tightly bounded provider code;
            # never propagate response bodies, object URLs or credentials.
            error = StorageError('Storage service request failed.')
            error.status = exc.code
            try:
                body = json.loads(exc.read(16 * 1024))
                if isinstance(body, dict):
                    code = body.get('code', '')
                    reason = body.get('error', '')
                    provider_status = body.get('statusCode')
                    if isinstance(code, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', code):
                        error.provider_code = code
                    if isinstance(reason, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', reason):
                        error.provider_reason = reason
                    if str(provider_status).isdigit() and 100 <= int(provider_status) <= 599:
                        error.provider_status = int(provider_status)
            except Exception:
                pass
            raise error from None
        except StorageError:
            raise
        except Exception:
            raise StorageError('Storage service is temporarily unavailable.') from None

    def verify_private(self):
        raw = self._request('GET', 'bucket/' + quote(self.bucket, safe=''))
        try:
            info = json.loads(raw)
        except Exception:
            raise StorageError('Could not verify the storage bucket.') from None
        if not isinstance(info, dict) or info.get('id') != self.bucket or info.get('public') is not False:
            raise StorageError('The storage bucket is missing or not private.')

    def put(self, key: str, content: bytes, mime: str):
        if not isinstance(content, bytes) or not content:
            raise StorageError('Cannot upload an empty object.')
        if not re.fullmatch(r'[a-z0-9.+-]+/[a-z0-9.+-]+', mime):
            mime = 'application/octet-stream'
        path = 'object/' + quote(self.bucket, safe='') + '/' + self._key(key)
        self._request('POST', path, data=content, content_type=mime)

    def get(self, key: str, max_bytes: int) -> bytes:
        path = 'object/authenticated/' + quote(self.bucket, safe='') + '/' + self._key(key)
        return self._request('GET', path, max_bytes=max_bytes)

    def delete(self, key: str):
        path = 'object/' + quote(self.bucket, safe='') + '/' + self._key(key)
        try:
            self._request('DELETE', path)
        except StorageError as exc:
            # Supabase's Storage API can report a missing object as HTTP 400
            # with code NoSuchKey (confirmed against the actual project), not
            # only as HTTP 404. Never confuse a missing bucket or permission
            # failure with successful cleanup.
            code = getattr(exc, 'provider_code', '')
            missing = ((getattr(exc, 'status', None) == 404 and code in ('', 'NoSuchKey')) or
                       (getattr(exc, 'status', None) == 400 and code == 'NoSuchKey' and
                        getattr(exc, 'provider_status', None) == 404 and
                        getattr(exc, 'provider_reason', '') == 'not_found'))
            if not missing:
                raise
            # Idempotent success only if the same credential can still verify
            # that the target bucket exists and is private.
            self.verify_private()
