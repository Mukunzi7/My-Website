# EduBridge PostgreSQL Production Setup

The current EduBridge app still runs on SQLite by default for easy local development. PostgreSQL production schema and setup files are now included so the platform can be moved to a real production database when deployed.

## Why PostgreSQL

Use PostgreSQL for public launch because:

- SQLite local files can be lost on some cloud platforms.
- PostgreSQL supports many concurrent users better.
- Backups, migrations, and scaling are easier.

## Recommended providers

- Google Cloud SQL for PostgreSQL
- Supabase PostgreSQL
- Neon PostgreSQL
- Railway PostgreSQL
- Render PostgreSQL

## Environment variable to use later

```bash
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/edubridge
```

## Migration path

1. Create a PostgreSQL database.
2. Run `database_postgresql.sql` to create tables.
3. Export SQLite data if needed.
4. Import into PostgreSQL.
5. Switch the application database adapter from SQLite to PostgreSQL.

## Important note

This project now includes the PostgreSQL schema, but the current zero-dependency Python server still uses SQLite directly. The next backend upgrade should replace direct `sqlite3` calls with SQLAlchemy or a small psycopg adapter so `DATABASE_URL` is used automatically.

For now, this is production-preparation, not a full database-engine switch.
