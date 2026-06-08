# Operating devdash

## devdash owns its own database (ADR-D07)

devdash provisions, migrates, and owns an entire Postgres database — not a schema
borrowed inside the host's DB. Point `DEVDASH_DATABASE_URL` at a database devdash
owns end to end.

### Quick start (dev / standalone)

```bash
# SQLite (zero infra) — the default
python -m devdash db create        # provisions + migrates
python -m devdash serve            # serves API + UI at http://127.0.0.1:8000/dev
```

### Production: owner / app role split

Run migrations as an **owner** role and the app as a least-privilege **app**
role, so runtime credentials can never issue DDL.

```sql
-- as a Postgres superuser, once:
CREATE ROLE devdash_owner LOGIN PASSWORD '...';
CREATE ROLE devdash_app   LOGIN PASSWORD '...';
CREATE DATABASE devdash OWNER devdash_owner;

\connect devdash
GRANT USAGE ON SCHEMA public TO devdash_app;
ALTER DEFAULT PRIVILEGES FOR ROLE devdash_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO devdash_app;
ALTER DEFAULT PRIVILEGES FOR ROLE devdash_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO devdash_app;
```

- **Migrations** (`devdash.migrate`, run by `db create` or your release pipeline)
  connect as `devdash_owner`. Migrations are **expand-only** and take a Postgres
  transaction advisory lock, so concurrent blue/green replicas cannot double-apply.
- **Runtime** (`DEVDASH_DATABASE_URL` with `auto_migrate=False`) connects as
  `devdash_app`.

```bash
# release pipeline (owner):
DEVDASH_DATABASE_URL=postgresql+asyncpg://devdash_owner:...@db/devdash \
  python -m devdash db create

# runtime (app, no DDL):
DEVDASH_DATABASE_URL=postgresql+asyncpg://devdash_app:...@db/devdash \
DEVDASH_AUTO_MIGRATE=false python -m devdash serve
```
