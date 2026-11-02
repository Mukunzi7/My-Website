#!/usr/bin/env python3
"""Safely import a VERIFIED v21 SQLite backup + uploads into a NEW PostgreSQL schema.

This tool is intentionally not a website endpoint. It never reads Render's running
filesystem, never replaces an existing target schema, and cannot recover files lost by
Render. Keep the original backup independently. Use a consistent SQLite snapshot and
its corresponding complete uploads directory; freeze/reconcile writes before cutover.
DATABASE_URL is read from the environment or a hidden prompt, never a command argument.
The tool uses a temporary private schema and publishes it only after verification.
"""
from __future__ import annotations
import argparse
import getpass
import hashlib
import mimetypes
import os
import re
import secrets
import sqlite3
import sys
from pathlib import Path

import pg_compat
import server

try:
    from psycopg import sql
except ImportError:
    sql = None

# Parent tables precede children so foreign keys remain enabled during import.
TABLES = (
    'users', 'opportunities', 'projects', 'settings', 'slideshow_photos',
    'feed_sources', 'sync_logs', 'sessions', 'assets', 'pledges', 'bookmarks',
    'payments', 'email_tokens', 'moderation_logs', 'project_messages',
    'opportunity_submissions', 'course_enrolments', 'message_incidents',
    'disbursements',
)


class MigrationError(Exception):
    pass


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _checked_file(root: Path, relative: str) -> Path:
    """Permit only ordinary files contained beneath the supplied uploads folder."""
    candidate = root / relative
    if candidate.is_symlink():
        raise MigrationError('An upload is a symbolic link; use a complete, ordinary file backup.')
    resolved = candidate.resolve()
    if root not in resolved.parents or not resolved.is_file():
        raise MigrationError('A referenced upload is missing from the backup.')
    return resolved


def _source_records(src: sqlite3.Connection, uploads: Path):
    """Validate the v21 database and locate every file the app currently references."""
    if src.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise MigrationError('The SQLite backup did not pass its integrity check.')
    if src.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise MigrationError('The SQLite backup contains broken foreign-key references.')
    present = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    if present != set(TABLES):
        raise MigrationError('The source is not the expected v21 schema; no data was imported.')
    markers = {r[0] for r in src.execute("SELECT key FROM settings WHERE key IN ('v18_privacy_migration','v19_slideshow_seeded')")}
    if markers != {'v18_privacy_migration', 'v19_slideshow_seeded'}:
        raise MigrationError('The source is missing v21 security/slideshow markers.')

    media = []
    referenced = set()
    for row in src.execute('SELECT id,profile_photo_url FROM users WHERE profile_photo_url<>\'\''):
        uid, url = row
        match = re.fullmatch(r'/uploads/profiles/(user-(\d+)-[a-f0-9]+\.(?:jpg|jpeg|png|gif|webp))', url, re.I)
        if not match or int(match.group(2)) != uid:
            raise MigrationError('A profile photo has an unsupported or mismatched path.')
        relative = 'profiles/' + match.group(1)
        path = _checked_file(uploads, relative)
        key = relative
        media.append((key, uid, None, mimetypes.guess_type(path.name)[0] or 'application/octet-stream', path, None))
        referenced.add(path)

    for row in src.execute('SELECT a.id,a.user_id,a.project_id,a.stored_path,a.mime,a.size,p.user_id FROM assets a JOIN projects p ON p.id=a.project_id'):
        asset_id, uid, pid, stored, mime, size, project_owner = row
        if uid != project_owner:
            raise MigrationError('A project file owner does not match its project owner.')
        name = Path(stored).name if stored else ''
        if not re.fullmatch(rf'{pid}-[a-f0-9]{{16}}-[A-Za-z0-9._-]+', name):
            raise MigrationError('A project file has an unsupported or missing local path.')
        path = _checked_file(uploads, name)
        if path.stat().st_size != size:
            raise MigrationError('A project file size differs from its database record.')
        key = 'assets/' + name
        media.append((key, uid, pid, mime, path, asset_id))
        referenced.add(path)

    if len({item[0] for item in media}) != len(media):
        raise MigrationError('The backup contains duplicate upload paths.')
    # Bundled slides must still exist in this code version; uploaded slides are DB blobs.
    slides_dir = (server.STATIC_DIR / 'images' / 'slides').resolve()
    for (name,) in src.execute("SELECT bundled_path FROM slideshow_photos WHERE bundled_path<>''"):
        file = (slides_dir / name).resolve()
        if file.parent != slides_dir or not file.is_file():
            raise MigrationError('A referenced bundled slideshow photo is missing from the code.')

    # A full uploads backup may contain old, no-longer-referenced files. They remain in
    # the original private backup; do not silently claim they were imported as active media.
    all_files = set()
    for directory, dirs, files in os.walk(uploads, followlinks=False):
        for entry in dirs:
            if (Path(directory) / entry).is_symlink():
                raise MigrationError('The uploads backup contains a symbolic-link directory.')
        for entry in files:
            file = Path(directory) / entry
            if file.is_symlink():
                raise MigrationError('The uploads backup contains a symbolic-link file.')
            if file.is_file(): all_files.add(file.resolve())
    return media, len(all_files - referenced)


def inspect_backup(sqlite_backup: Path, uploads_folder: Path) -> dict:
    """Check a local offline backup without connecting to or changing any database."""
    database = Path(sqlite_backup).resolve()
    uploads = Path(uploads_folder).resolve()
    if not database.is_file() or not uploads.is_dir():
        raise MigrationError('A SQLite backup file and complete uploads directory are required.')
    src = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    try:
        src.execute('PRAGMA query_only=ON')
        src.execute('BEGIN')
        media, orphan_count = _source_records(src, uploads)
        counts = {table: src.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in TABLES}
        return {'source_counts': counts, 'referenced_uploads': len(media),
                'unreferenced_uploads_in_backup': orphan_count,
                'referenced_upload_bytes': sum(path.stat().st_size for _, _, _, _, path, _ in media)}
    finally:
        src.close()


def _verify_table_rows(src, conn, schema, table, columns):
    """Compare every source column without logging any of its private values."""
    info = src.execute(f'PRAGMA table_info("{table}")').fetchall()
    primary = [row[1] for row in sorted((r for r in info if r[5]), key=lambda r: r[5])]
    if not primary:
        raise MigrationError('A source table has no primary key; cannot verify its rows.')
    source_names = ', '.join('"' + c.replace('"', '""') + '"' for c in columns)
    source_order = ', '.join('"' + c.replace('"', '""') + '"' for c in primary)
    source_rows = src.execute(f'SELECT {source_names} FROM "{table}" ORDER BY {source_order}')
    target_names = sql.SQL(', ').join(sql.Identifier(c) for c in columns)
    # The only text primary keys are ASCII token hashes and setting keys. Force the
    # PostgreSQL C collation to match SQLite's binary ordering regardless of locale.
    ordering = sql.SQL(', ').join(
        sql.SQL('{} COLLATE "C"').format(sql.Identifier(c)) if table in ('sessions', 'settings')
        else sql.Identifier(c) for c in primary)
    query = sql.SQL('SELECT {} FROM {} ORDER BY {}').format(
        target_names, sql.Identifier(schema, table), ordering)
    with conn.cursor(name='verify_' + table) as cur:
        cur.execute(query)
        for source_row in source_rows:
            target = cur.fetchone()
            if target is None:
                raise MigrationError('A copied table has missing rows.')
            left = tuple(bytes(v) if isinstance(v, memoryview) else v for v in source_row)
            right = tuple(bytes(target[c]) if isinstance(target[c], memoryview) else target[c] for c in columns)
            if left != right:
                raise MigrationError('A copied row differs from the backup; refusing cutover.')
        if cur.fetchone() is not None:
            raise MigrationError('A copied table has extra rows.')


def migrate(sqlite_backup: Path, uploads_folder: Path, database_url: str,
            target_schema: str = 'scholar_data') -> dict:
    """Copy an offline snapshot into an absent target schema; return counts only.

    On error the source and any pre-existing schema are untouched. A random temporary
    schema is removed if possible. No personal records or passwords are printed.
    """
    if not database_url or sql is None:
        raise MigrationError('A private PostgreSQL connection and psycopg are required.')
    target_schema = pg_compat._schema(target_schema)
    if target_schema.startswith('import_'):
        raise MigrationError('The final schema cannot use the reserved import prefix.')
    database = Path(sqlite_backup).resolve()
    uploads = Path(uploads_folder).resolve()
    if not database.is_file() or not uploads.is_dir():
        raise MigrationError('A SQLite backup file and complete uploads directory are required.')

    # Read-only source plus a consistent read transaction; the backup itself remains unchanged.
    src = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    temp_schema = 'import_' + secrets.token_hex(12)
    created = False
    renamed = False
    previous = (server.DATABASE_URL, server.PG_SCHEMA, server.UPLOAD_DIR)
    try:
        src.execute('PRAGMA query_only=ON')
        src.execute('BEGIN')
        media, orphan_count = _source_records(src, uploads)
        counts = {table: src.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in TABLES}
        # Hash before copying, then compare against the actual PostgreSQL bytes later.
        expected_hashes = {key: _file_digest(path) for key, _, _, _, path, _ in media}

        with pg_compat._connect(database_url) as conn:
            exists = conn.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s', (target_schema,)).fetchone()
            if exists:
                raise MigrationError('The target schema already exists; refusing to replace or merge it.')
            # CREATE without IF NOT EXISTS: never treat somebody else's schema as ours.
            conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(temp_schema)))
        created = True
        server.DATABASE_URL, server.PG_SCHEMA, server.UPLOAD_DIR = database_url, temp_schema, uploads
        server.init_db()  # Creates tables only inside our random, private staging schema.
        with pg_compat._connect(database_url) as conn:
            target_names = sql.SQL(', ').join(sql.Identifier(temp_schema, table) for table in TABLES + ('media_objects',))
            conn.execute(sql.SQL('TRUNCATE {} RESTART IDENTITY').format(target_names))
            for table in TABLES:
                columns = [r[1] for r in src.execute(f'PRAGMA table_info("{table}")')]
                target_columns = {r['column_name'] for r in conn.execute(
                    'SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s',
                    (temp_schema, table)).fetchall()}
                if not set(columns).issubset(target_columns):
                    raise MigrationError('A source column has no destination; refusing to omit data.')
                identifiers = sql.SQL(', ').join(sql.Identifier(c) for c in columns)
                placeholders = sql.SQL(', ').join(sql.Placeholder() for _ in columns)
                insert = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
                    sql.Identifier(temp_schema, table), identifiers, placeholders)
                rows = src.execute(f'SELECT * FROM "{table}"')
                with conn.cursor() as cur:
                    while True:
                        batch = rows.fetchmany(20)
                        if not batch: break
                        cur.executemany(insert, batch)
                _verify_table_rows(src, conn, temp_schema, table, columns)

            for key, uid, pid, mime, path, asset_id in media:
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != expected_hashes[key]:
                    raise MigrationError('An upload changed while the migration was running.')
                conn.execute(sql.SQL('INSERT INTO {} (storage_key,owner_id,project_id,mime,data,created_at) VALUES (%s,%s,%s,%s,%s,%s)').format(
                    sql.Identifier(temp_schema, 'media_objects')), (key, uid, pid, mime, data, server.now_iso()))
                if asset_id is not None:
                    conn.execute(sql.SQL('UPDATE {} SET stored_path=%s WHERE id=%s').format(
                        sql.Identifier(temp_schema, 'assets')), ('db:' + key, asset_id))
                stored = conn.execute(sql.SQL('SELECT data FROM {} WHERE storage_key=%s').format(
                    sql.Identifier(temp_schema, 'media_objects')), (key,)).fetchone()['data']
                if hashlib.sha256(stored).hexdigest() != expected_hashes[key]:
                    raise MigrationError('A copied upload failed its checksum.')
            for table, expected in counts.items():
                actual = conn.execute(sql.SQL('SELECT COUNT(*) AS n FROM {}').format(sql.Identifier(temp_schema, table))).fetchone()['n']
                if actual != expected:
                    raise MigrationError('A table row count did not match; refusing cutover.')
            # Preserve SQLite's AUTOINCREMENT high-water marks even if a high-ID row
            # was deleted. Reusing deleted IDs could revive old slide/download URLs.
            old_sequences = dict(src.execute('SELECT name,seq FROM sqlite_sequence'))
            for table in pg_compat.SERIAL_TABLES.intersection(TABLES):
                row = conn.execute(sql.SQL('SELECT COALESCE(MAX(id),0) AS max_id FROM {}').format(
                    sql.Identifier(temp_schema, table))).fetchone()
                previous_high = max(int(old_sequences.get(table) or 0), int(row['max_id']))
                conn.execute("SELECT setval(pg_get_serial_sequence(%s,'id'), %s, %s)",
                             (f'{temp_schema}.{table}', max(previous_high, 1), previous_high > 0))
        # Run the new-version migrations/seeding only after the original rows are verified.
        server.init_db()
        with pg_compat._connect(database_url) as conn:
            for table in ('users', 'projects', 'assets', 'settings', 'slideshow_photos'):
                if table == 'settings':
                    continue  # The app may add version-specific settings.
                actual = conn.execute(sql.SQL('SELECT COUNT(*) AS n FROM {}').format(sql.Identifier(temp_schema, table))).fetchone()['n']
                if actual != counts[table]:
                    raise MigrationError('Post-import validation changed an important record count.')
            exists = conn.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s', (target_schema,)).fetchone()
            if exists:
                raise MigrationError('The target schema appeared during import; refusing to replace it.')
            conn.execute(sql.SQL('ALTER SCHEMA {} RENAME TO {}').format(
                sql.Identifier(temp_schema), sql.Identifier(target_schema)))
        renamed = True
        return {'source_counts': counts, 'referenced_uploads': len(media), 'unreferenced_uploads_in_backup': orphan_count}
    finally:
        server.DATABASE_URL, server.PG_SCHEMA, server.UPLOAD_DIR = previous
        src.close()
        if created and not renamed:
            try:
                with pg_compat._connect(database_url) as conn:
                    conn.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(temp_schema)))
            except Exception:
                # It remains a private randomly named import schema, never the target.
                print('Warning: a temporary private import schema may need cleanup by the operator.', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', type=Path, required=True, help='private, consistent v21 SQLite backup')
    parser.add_argument('--uploads', type=Path, required=True, help='matching complete uploads directory')
    parser.add_argument('--verify-only', action='store_true', help='check the local backup; do not contact PostgreSQL')
    args = parser.parse_args()
    if args.verify_only:
        try:
            result = inspect_backup(args.sqlite, args.uploads)
        except Exception as exc:
            print('Backup validation failed. Reason:', str(exc) if isinstance(exc, MigrationError) else type(exc).__name__, file=sys.stderr)
            return 1
        print('Local backup checks passed. Counts:', ', '.join(f'{k}={v}' for k, v in result['source_counts'].items()))
        print('Referenced uploads:', result['referenced_uploads'], 'bytes:', result['referenced_upload_bytes'])
        print('Unreferenced uploads retained in the original backup:', result['unreferenced_uploads_in_backup'])
        print('No database was contacted or changed. This does not prove the backup contains the latest live writes.')
        return 0
    print('This imports a verified OFFLINE backup into a NEW scholar_data schema. It cannot fetch or protect live Render files.')
    print('Keep the original backup private and ensure no writes are missed during the eventual cutover.')
    if input('Type IMPORT to confirm you have a consistent private backup and an empty target schema: ').strip() != 'IMPORT':
        print('Cancelled. No data was changed.'); return 1
    url = os.environ.get('DATABASE_URL', '').strip() or getpass.getpass('PostgreSQL session-pooler URL (hidden): ').strip()
    try:
        result = migrate(args.sqlite, args.uploads, url)
    except Exception as exc:
        # Database errors may include private values or credentials; do not print them.
        print('Import stopped; the original backup and any existing target were not replaced.', file=sys.stderr)
        print('Reason:', str(exc) if isinstance(exc, MigrationError) else type(exc).__name__, file=sys.stderr)
        return 1
    print('Import verified. Counts:', ', '.join(f'{k}={v}' for k, v in result['source_counts'].items()))
    print('Referenced uploads copied:', result['referenced_uploads'])
    print('Unreferenced files retained only in your original backup:', result['unreferenced_uploads_in_backup'])
    print('This has NOT switched the live website. Verify the target privately before planning a cutover.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
