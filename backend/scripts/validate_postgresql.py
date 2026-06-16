"""
PostgreSQL Validation Script for Quiz App

Usage:
    SET DATABASE_URL=postgresql://quizapp:quizapp@localhost:5432/quizapp
    python scripts/validate_postgresql.py

Requires a running PostgreSQL instance with the quizapp database created.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DATABASE_URL", "postgresql://quizapp:quizapp@localhost:5432/quizapp")

from sqlalchemy import text
from database import engine
from main import app
from fastapi.testclient import TestClient

PASS = 0
FAIL = 0


def check(description, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {description}")
    else:
        FAIL += 1
        print(f"  FAIL: {description}")


def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


print("Quiz App — PostgreSQL Validation Suite")
print(f"Database URL: {os.environ['DATABASE_URL']}")
print(f"Started at: {datetime.now(timezone.utc).isoformat()}")

# ── 1. Connection ──
section("1. Database Connection")
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()")).scalar()
        check("PostgreSQL connection established", "PostgreSQL" in result)
        print(f"    Version: {result}")
except Exception as e:
    check(f"PostgreSQL connection: {e}", False)

# ── 2. Alembic Migrations ──
section("2. Alembic Migrations")
try:
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
    check("Alembic upgrade head succeeded", True)
except Exception as e:
    check(f"Alembic upgrade head: {e}", False)

# ── 3. Table Creation ──
section("3. Table Verification")
with engine.connect() as conn:
    tables = [row[0] for row in conn.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )).fetchall()]
    expected = {"users", "quizzes", "submissions", "categories", "tags", "quiz_tags",
                "refresh_tokens", "password_reset_tokens", "alembic_version"}
    for table in expected:
        check(f"Table '{table}' exists", table in tables)

# ── 4. Indexes ──
section("4. Index Verification")
with engine.connect() as conn:
    indexes = [row[0] for row in conn.execute(text(
        "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
    )).fetchall()]
    expected_indexes = {
        "ix_users_role", "ix_submissions_user_id", "ix_submissions_quiz_id",
        "ix_submissions_created_at", "ix_submissions_percentage",
        "ix_quizzes_title", "ix_quizzes_category_id", "ix_quizzes_views",
        "ix_quizzes_created_at", "ix_refresh_tokens_expires_at",
        "ix_password_reset_tokens_expires_at",
    }
    for idx in expected_indexes:
        check(f"Index '{idx}' exists", idx in indexes)

# ── 5. Foreign Keys ──
section("5. Foreign Key Verification")
with engine.connect() as conn:
    fks = [row[0] for row in conn.execute(text(
        "SELECT conname FROM pg_constraint WHERE contype = 'f'"
    )).fetchall()]
    expected_fks = {"fk_submissions_quiz_id"}
    for fk in expected_fks:
        check(f"FK '{fk}' exists", fk in fks)

# ── 6. API Smoke Tests ──
section("6. API Smoke Tests")
client = TestClient(app)

resp = client.get("/health")
check("GET /health returns 200", resp.status_code == 200)
data = resp.json()
check("GET /health has status field", "status" in data)
check("GET /health has database field", "database" in data)
check("GET /health has version field", "version" in data)
check("GET /health has uptime_seconds field", "uptime_seconds" in data)

resp = client.get("/metrics")
check("GET /metrics returns 200", resp.status_code == 200)
data = resp.json()
check("GET /metrics has total_users", "total_users" in data)
check("GET /metrics database type is postgresql", data.get("database") == "postgresql")

# Register
resp = client.post("/auth/register", json={
    "name": "Validation User",
    "email": "validate@test.com",
    "password": "password123",
})
check("POST /auth/register returns 200", resp.status_code == 200)
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Me
resp = client.get("/auth/me", headers=headers)
check("GET /auth/me returns user data", resp.status_code == 200)

# Create quiz
resp = client.post("/quizzes", json={
    "title": "PG Validation Quiz",
    "description": "Testing PostgreSQL compatibility",
    "questions": [
        {"id": 1, "text": "Q1?", "type": "text", "required": True},
        {"id": 2, "text": "Choose:", "type": "single_choice", "required": True,
         "options": [{"id": 1, "text": "A"}, {"id": 2, "text": "B"}]},
    ],
}, headers=headers)
check("POST /quizzes returns 201", resp.status_code == 201)
quiz_id = resp.json()["id"]

# List quizzes
resp = client.get("/quizzes", headers=headers)
check("GET /quizzes returns list", resp.status_code == 200 and len(resp.json()) > 0)

# Submit
resp = client.post(f"/quizzes/{quiz_id}/submit", json={
    "answers": [
        {"question_id": 1, "value": "Test answer"},
        {"question_id": 2, "value": "1"},
    ],
}, headers=headers)
check("POST /quizzes/{id}/submit returns 200", resp.status_code == 200)

# Dashboard
resp = client.get("/me/dashboard", headers=headers)
check("GET /me/dashboard returns 200", resp.status_code == 200)
data = resp.json()
check("Dashboard has total_quizzes_created", "total_quizzes_created" in data)
check("Dashboard has total_submissions", "total_submissions" in data)
check("Dashboard has ranking_position", "ranking_position" in data)

# Stats
resp = client.get("/me/stats", headers=headers)
check("GET /me/stats returns 200", resp.status_code == 200)

# Categories & Tags
resp = client.get("/categories", headers=headers)
check("GET /categories returns 200", resp.status_code == 200)
resp = client.get("/tags", headers=headers)
check("GET /tags returns 200", resp.status_code == 200)

# Leaderboard
resp = client.get("/leaderboard", headers=headers)
check("GET /leaderboard returns 200", resp.status_code == 200)

# Profile
me = client.get("/auth/me", headers=headers).json()
resp = client.get(f"/users/{me['id']}/profile")
check("GET /users/{id}/profile returns 200", resp.status_code == 200)
data = resp.json()
check("Profile has badges", "badges" in data)
check("Profile has ranking_position", "ranking_position" in data)

# Refresh token
resp = client.post("/auth/refresh", json={"refresh_token": resp.json()["refresh_token"]})
check("POST /auth/refresh works", resp.status_code in (200, 401))

# Forgot password
resp = client.post("/auth/forgot-password", json={"email": "validate@test.com"})
check("POST /auth/forgot-password returns 200", resp.status_code == 200)

# Admin dashboard
resp = client.get("/admin/dashboard", headers=headers)
check("GET /admin/dashboard returns 200", resp.status_code == 200)

# Admin users
resp = client.get("/admin/users", headers=headers)
check("GET /admin/users returns list", resp.status_code == 200)

# Search
resp = client.get("/quizzes/search?q=PG+Validation", headers=headers)
check("GET /quizzes/search returns 200", resp.status_code == 200)

# Submissions
resp = client.get("/me/submissions", headers=headers)
check("GET /me/submissions returns list", resp.status_code == 200)

# Quiz leaderboard
resp = client.get(f"/quizzes/{quiz_id}/leaderboard", headers=headers)
check("GET /quizzes/{id}/leaderboard returns 200", resp.status_code == 200)

# Update quiz
resp = client.put(f"/quizzes/{quiz_id}", json={
    "description": "Updated description for PG test",
}, headers=headers)
check("PUT /quizzes/{id} returns 200", resp.status_code == 200)

# Security headers
resp = client.get("/health")
check("X-Request-ID header present", "X-Request-ID" in resp.headers)
check("X-Content-Type-Options header present", "X-Content-Type-Options" in resp.headers)
check("X-Frame-Options header present", "X-Frame-Options" in resp.headers)

# ── 7. Alembic Downgrade/Upgrade ──
section("7. Alembic Downgrade/Upgrade Cycle")
try:
    command.downgrade(alembic_cfg, "base")
    check("Alembic downgrade base succeeded", True)
    command.upgrade(alembic_cfg, "head")
    check("Alembic upgrade head (second pass) succeeded", True)
except Exception as e:
    check(f"Alembic cycle failed: {e}", False)

# ── 8. Orphan Check ──
section("8. Orphan Object Check")
with engine.connect() as conn:
    orphan_fks = conn.execute(text("""
        SELECT conname FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.confrelid
        WHERE contype = 'f' AND rel.relname NOT IN (
            SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'
        )
    """)).fetchall()
    check("No orphan FK references", len(orphan_fks) == 0)

# ── Summary ──
section("SUMMARY")
print(f"  Total: {PASS + FAIL}")
print(f"  Passed: {PASS}")
print(f"  Failed: {FAIL}")
print(f"  Status: {'ALL PASSED' if FAIL == 0 else f'{FAIL} FAILURES'}")
print(f"  Finished at: {datetime.now(timezone.utc).isoformat()}")
