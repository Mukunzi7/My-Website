"""Narrow compatibility layer for 70Scholar's existing SQLite SQL on PostgreSQL.

The app owns its SQL: this isn't a general-purpose SQL translator. It keeps SQLite
available for development while PostgreSQL provides durable hosted storage. No
connection string or record data should ever be logged.
"""
from __future__ import annotations
import atexit
import os
import re
import ssl
import tempfile
from pathlib import Path
from urllib.parse import urlparse

_CA_FILE = None


def _ssl_root(host=''):
    """Choose an operator-provided CA, Supabase's public root, or system roots."""
    global _CA_FILE
    pem = os.environ.get('SUPABASE_DB_CA_PEM', '').strip()
    if not pem:
        explicit = os.environ.get('PG_SSL_ROOT_CERT', '').strip()
        if explicit:
            return explicit
        if host.endswith('.pooler.supabase.com'):
            # Public certificate downloaded from Supabase's official CA endpoint.
            # It is NOT a credential; verify-full still checks the actual hostname.
            ca = Path(__file__).resolve().parent / 'certs' / 'supabase-root-2021.crt'
            if not ca.is_file():
                raise RuntimeError('Supabase CA certificate is missing')
            return str(ca)
        return 'system'
    if _CA_FILE is None:
        if len(pem) > 32768 or 'PRIVATE KEY' in pem:
            raise RuntimeError('SUPABASE_DB_CA_PEM must contain only CA certificates')
        try:
            ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).load_verify_locations(cadata=pem)
        except (ssl.SSLError, ValueError) as exc:
            raise RuntimeError('SUPABASE_DB_CA_PEM is not a valid PEM CA certificate') from exc
        # Certificate material is public; nevertheless use a restricted temporary file.
        fd, _CA_FILE = tempfile.mkstemp(prefix='70scholar-ca-', suffix='.pem')
        with os.fdopen(fd, 'w', encoding='ascii') as f:
            f.write(pem + '\n')
        def cleanup(path=_CA_FILE):
            try: os.unlink(path)
            except OSError: pass
        atexit.register(cleanup)
    return _CA_FILE

try:
    import psycopg
except ImportError:  # Local SQLite development doesn't require the driver.
    psycopg = None

SCHEMA_DEFAULT = 'scholar_data'
SERIAL_TABLES = {
    'users', 'opportunities', 'projects', 'assets', 'pledges', 'payments',
    'sync_logs', 'email_tokens', 'moderation_logs', 'project_messages',
    'slideshow_photos', 'feed_sources', 'opportunity_submissions',
    'course_enrolments', 'message_incidents', 'disbursements',
}

class HybridRow(dict):
    """sqlite3.Row-like access by name or position; no data is logged."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)

def row_factory(cursor):
    names = [column.name for column in cursor.description] if cursor.description else []
    def make(values):
        row = HybridRow()
        for name, value in zip(names, values):
            if name not in row:  # sqlite3.Row uses the first duplicate column name.
                row[name] = value
        return row
    return make

def _connect(url: str):
    if psycopg is None:
        raise RuntimeError('PostgreSQL driver missing; install requirements.txt')
    host = (urlparse(url).hostname or '').lower()
    if not host:
        raise RuntimeError('DATABASE_URL must contain a PostgreSQL host')
    options = {'connect_timeout': 12, 'prepare_threshold': None, 'row_factory': row_factory}
    if host in ('127.0.0.1', 'localhost', '::1'):
        # Only local test connections are allowed without TLS.
        if os.environ.get('RENDER', '').lower() == 'true':
            raise RuntimeError('Render requires a TLS-authenticated remote database')
        options['sslmode'] = 'disable'
    else:
        # Encrypt and authenticate the database server, never fall back to plaintext.
        options['sslmode'] = 'verify-full'
        options['sslrootcert'] = _ssl_root(host)
    return psycopg.connect(url, **options)

def _schema(schema):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,48}', schema or ''):
        raise ValueError('Invalid private database schema name')
    return schema

def ensure_private_schema(url: str, schema: str = SCHEMA_DEFAULT):
    """Create a non-exposed schema and remove default browser/API roles' grants."""
    schema = _schema(schema)
    with _connect(url) as conn:
        conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        # A new custom schema is not an exposed Supabase API schema by default.
        # Remove direct privileges too, including those created by provider defaults.
        conn.execute(f'REVOKE ALL ON SCHEMA "{schema}" FROM PUBLIC')
        roles = [row['rolname'] for row in conn.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated','service_role')").fetchall()]
        for role in roles:
            conn.execute(f'REVOKE ALL ON SCHEMA "{schema}" FROM "{role}"')
            conn.execute(f'REVOKE ALL ON ALL TABLES IN SCHEMA "{schema}" FROM "{role}"')
            conn.execute(f'REVOKE ALL ON ALL SEQUENCES IN SCHEMA "{schema}" FROM "{role}"')
            conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" REVOKE ALL ON TABLES FROM "{role}"')
            conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" REVOKE ALL ON SEQUENCES FROM "{role}"')
        conn.execute(f'REVOKE ALL ON ALL TABLES IN SCHEMA "{schema}" FROM PUBLIC')
        conn.execute(f'REVOKE ALL ON ALL SEQUENCES IN SCHEMA "{schema}" FROM PUBLIC')
        conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" REVOKE ALL ON TABLES FROM PUBLIC')
        conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" REVOKE ALL ON SEQUENCES FROM PUBLIC')

def _translate(sql: str, parameters):
    """Translate only constructs currently used in 70Scholar's SQL."""
    sql = sql.strip().rstrip(';')
    if sql.upper() == 'BEGIN IMMEDIATE':
        # Serialize the app's critical token, slideshow and disbursement transactions.
        return 'SELECT pg_advisory_xact_lock(701907018)', None, False
    sql = re.sub(r'\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b', 'BIGSERIAL PRIMARY KEY', sql, flags=re.I)
    sql = re.sub(r'\bBLOB\b', 'BYTEA', sql, flags=re.I)
    sql = re.sub(r'\bREAL\b', 'DOUBLE PRECISION', sql, flags=re.I)
    sql = re.sub(r'\s+COLLATE\s+NOCASE\b', '', sql, flags=re.I)
    sql = re.sub(r'\bADD\s+COLUMN\s+(?!IF\s+NOT\s+EXISTS)', 'ADD COLUMN IF NOT EXISTS ', sql, flags=re.I)
    # SQLite LIKE is ASCII-case-insensitive; ILIKE is the close PostgreSQL equivalent.
    sql = re.sub(r'\bLIKE\b', 'ILIKE', sql, flags=re.I)
    is_ignore = bool(re.match(r'INSERT\s+OR\s+IGNORE\s+INTO\b', sql, re.I))
    sql = re.sub(r'^INSERT\s+OR\s+IGNORE\s+INTO\b', 'INSERT INTO', sql, flags=re.I)
    if is_ignore:
        sql += ' ON CONFLICT DO NOTHING'
    serial = re.match(r'^INSERT\s+INTO\s+([a-z_][a-z0-9_]*)\b', sql, re.I)
    returns_id = bool(serial and serial.group(1).lower() in SERIAL_TABLES)
    if returns_id:
        sql += ' RETURNING id'
    if parameters is not None:
        # psycopg's percent placeholders require literal % to be doubled.
        sql = sql.replace('%', '%%')
        if isinstance(parameters, dict):
            sql = re.sub(r':([a-zA-Z_][a-zA-Z_0-9]*)', r'%(\1)s', sql)
        else:
            sql = sql.replace('?', '%s')
    return sql, parameters, returns_id

class Cursor:
    def __init__(self, cursor, lastrowid=None):
        self._cursor = cursor
        self.lastrowid = lastrowid
        self.rowcount = cursor.rowcount
    def fetchone(self): return self._cursor.fetchone()
    def fetchall(self): return self._cursor.fetchall()
    def __iter__(self): return iter(self._cursor)

class Connection:
    def __init__(self, url: str, schema: str = SCHEMA_DEFAULT):
        schema = _schema(schema)
        self._raw = _connect(url)
        self._raw.execute(f'SET search_path TO "{schema}", pg_catalog')
    def execute(self, sql, parameters=None):
        sql, parameters, returns_id = _translate(sql, parameters)
        cur = self._raw.execute(sql) if parameters is None else self._raw.execute(sql, parameters)
        row = cur.fetchone() if returns_id else None
        return Cursor(cur, row['id'] if row else None)
    def executescript(self, script):
        # The app's schema scripts contain no procedural blocks or semicolons in strings.
        for statement in script.split(';'):
            if statement.strip(): self.execute(statement)
    def commit(self): self._raw.commit()
    def rollback(self): self._raw.rollback()
    def close(self): self._raw.close()
