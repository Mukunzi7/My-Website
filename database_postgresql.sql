-- Learnwella PostgreSQL production schema
-- Run this in a PostgreSQL database before migrating production data.

CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  salt TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'student',
  email_verified INTEGER NOT NULL DEFAULT 0,
  profile_photo_url TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  csrf TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunities (
  id BIGSERIAL PRIMARY KEY,
  type TEXT NOT NULL,
  title TEXT NOT NULL UNIQUE,
  provider TEXT NOT NULL,
  country TEXT NOT NULL,
  level TEXT NOT NULL,
  deadline TEXT NOT NULL,
  url TEXT NOT NULL,
  summary TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  summary TEXT NOT NULL,
  details TEXT NOT NULL,
  goal_amount NUMERIC NOT NULL DEFAULT 0,
  price NUMERIC NOT NULL DEFAULT 0,
  asset_url TEXT NOT NULL DEFAULT '',
  demo_url TEXT NOT NULL DEFAULT '',
  repo_url TEXT NOT NULL DEFAULT '',
  mobile_money_name TEXT NOT NULL DEFAULT '',
  mobile_money_number TEXT NOT NULL DEFAULT '',
  mobile_money_network TEXT NOT NULL DEFAULT '',
  payout_notes TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  stored_path TEXT NOT NULL,
  external_url TEXT NOT NULL DEFAULT '',
  mime TEXT NOT NULL,
  size BIGINT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pledges (
  id BIGSERIAL PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  message TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pledged',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookmarks (
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  opportunity_id BIGINT NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  PRIMARY KEY(user_id, opportunity_id)
);

CREATE TABLE IF NOT EXISTS payments (
  id BIGSERIAL PRIMARY KEY,
  pledge_id BIGINT NOT NULL REFERENCES pledges(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  reference TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  checkout_url TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_logs (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  imported BIGINT NOT NULL DEFAULT 0,
  message TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_tokens (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  purpose TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS moderation_logs (
  id BIGSERIAL PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  admin_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_email_tokens_hash ON email_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_opportunities_deadline ON opportunities(deadline);

CREATE TABLE IF NOT EXISTS project_messages (
  id BIGSERIAL PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_project_messages_project ON project_messages(project_id);
