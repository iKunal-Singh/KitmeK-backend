#!/usr/bin/env bash
set -euo pipefail
cd /home/kunal/projects/kitmeK-lesson-backend

echo "[DBEngineer] Waiting for arch_schema_done sentinel..."
while [ ! -f ".agent_signals/arch_schema_done" ]; do
  echo "[DBEngineer] Waiting... ($(date))"
  sleep 30
done
echo "[DBEngineer] Sentinel detected. Starting DB setup."

# ── 1. Start Postgres ──────────────────────────────────────────────────────
docker-compose up -d postgres
echo "[DBEngineer] Waiting for Postgres to be ready..."
until docker-compose exec -T postgres pg_isready -U kitmeK; do sleep 5; done
echo "[DBEngineer] Postgres is ready."

# ── 2. Apply schema ────────────────────────────────────────────────────────
docker cp db/schema.sql "$(docker-compose ps -q postgres)":/tmp/schema.sql
docker-compose exec -T postgres psql -U kitmeK -d lesson_generation -f /tmp/schema.sql
echo "[DBEngineer] Schema applied."

# ── 3. Install Python deps ─────────────────────────────────────────────────
pip install -r requirements.txt
echo "[DBEngineer] Python dependencies installed."

# ── 4. Alembic migrations ──────────────────────────────────────────────────
export DATABASE_URL="postgresql+asyncpg://kitmeK:dev_password@localhost:5432/lesson_generation"
if [ -f "db/alembic.ini" ]; then
  alembic -c db/alembic.ini upgrade head
  echo "[DBEngineer] Alembic migrations applied."
else
  echo "[DBEngineer] No alembic.ini found; skipping Alembic step."
fi

# ── 5. Apply performance indices ───────────────────────────────────────────
docker cp db/indices.sql "$(docker-compose ps -q postgres)":/tmp/indices.sql
docker-compose exec -T postgres psql -U kitmeK -d lesson_generation -f /tmp/indices.sql
echo "[DBEngineer] Indices applied."

# ── 6. Seed data ───────────────────────────────────────────────────────────
docker cp db/seed_data.sql "$(docker-compose ps -q postgres)":/tmp/seed.sql
docker-compose exec -T postgres psql -U kitmeK -d lesson_generation -f /tmp/seed.sql
echo "[DBEngineer] Seed data loaded."

# ── 7. Verify ──────────────────────────────────────────────────────────────
echo "=== Tables ==="
docker-compose exec -T postgres psql -U kitmeK -d lesson_generation -c "\dt"
echo "=== Topic count ==="
docker-compose exec -T postgres psql -U kitmeK -d lesson_generation -c "SELECT count(*) FROM topics;"

# ── 8. Write sentinel ─────────────────────────────────────────────────────
echo "done" > .agent_signals/db_migrations_done
echo "[DBEngineer] db_migrations_done sentinel written. All tasks complete."
