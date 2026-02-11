# Alembic Developer Workflow

This document explains the recommended Alembic workflow for development when using multiple DB backends.

Quick commands

- Create a new revision with autogenerate:

```bash
alembic revision --autogenerate -m "describe change"
```

- Apply migrations to the dev SQLite DB:

```powershell
$env:VS_DB_MODE='sqlite'; alembic upgrade head
```

- Show pending migrations:

```bash
alembic history --verbose
```

Notes
- Keep migrations dialect-agnostic: avoid raw SQL where possible.
- If adding database-specific constructs, guard them with `context.get_bind().dialect.name` checks in the migration script.
- Use `alembic.ini` and `env.py` already present in the repo.
