"""
Performance Smoke Test for Quiz App

Populates the database with sample data and measures endpoint response times.

Usage:
    SET DATABASE_URL=postgresql://quizapp:quizapp@localhost:5432/quizapp
    python scripts/performance_smoke.py
"""
import os
import sys
import time
import random
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DATABASE_URL", "postgresql://quizapp:quizapp@localhost:5432/quizapp")

from database import SessionLocal
from main import app
from fastapi.testclient import TestClient

NUM_USERS = 100
NUM_QUIZZES = 1000
NUM_SUBMISSIONS = 10000

client = TestClient(app)
db = SessionLocal()


def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}")


def time_endpoint(name, method, path, headers=None, json_data=None):
    start = time.time()
    if method == "GET":
        resp = client.get(path, headers=headers or {})
    elif method == "POST":
        resp = client.post(path, headers=headers or {}, json=json_data or {})
    elapsed = round((time.time() - start) * 1000)
    return elapsed, resp.status_code


log("=" * 60)
log("  Performance Smoke Test")
log(f"  Users: {NUM_USERS}, Quizzes: {NUM_QUIZZES}, Submissions: {NUM_SUBMISSIONS}")
log(f"  Database URL: {os.environ['DATABASE_URL']}")
log("=" * 60)

# ── Seed Data ──
log("Seeding data...")

tokens = []
for i in range(NUM_USERS):
    email = f"perfuser{i}@test.com"
    resp = client.post("/auth/register", json={
        "name": f"Perf User {i}",
        "email": email,
        "password": "password123",
    })
    if resp.status_code == 200:
        tokens.append(resp.json()["access_token"])
    else:
        log(f"  User {i} register failed: {resp.status_code}")
log(f"  Created {len(tokens)} users")

quiz_ids = []
quiz_creators = []
for i in range(NUM_QUIZZES):
    creator_idx = random.randint(0, len(tokens) - 1)
    resp = client.post("/quizzes", json={
        "title": f"Perf Quiz {i}",
        "description": f"Performance test quiz number {i}",
        "questions": [
            {"id": 1, "text": f"Question 1 for quiz {i}?", "type": "text", "required": True},
            {"id": 2, "text": "Rate this:", "type": "rating", "required": True,
             "options": [{"id": 1, "text": "1"}, {"id": 2, "text": "2"}, {"id": 3, "text": "3"}, {"id": 4, "text": "4"}, {"id": 5, "text": "5"}]},
            {"id": 3, "text": "Choose:", "type": "single_choice", "required": True,
             "options": [{"id": 1, "text": "A"}, {"id": 2, "text": "B"}, {"id": 3, "text": "C"}]},
        ],
    }, headers={"Authorization": f"Bearer {tokens[creator_idx]}"})
    if resp.status_code == 201:
        quiz_ids.append(resp.json()["id"])
        quiz_creators.append(creator_idx)
log(f"  Created {len(quiz_ids)} quizzes")

sub_count = 0
for i in range(NUM_SUBMISSIONS):
    user_idx = random.randint(0, len(tokens) - 1)
    if not quiz_ids:
        break
    q_idx = random.randint(0, len(quiz_ids) - 1)
    resp = client.post(f"/quizzes/{quiz_ids[q_idx]}/submit", json={
        "answers": [
            {"question_id": 1, "value": f"Answer {i}"},
            {"question_id": 2, "value": random.randint(1, 5)},
            {"question_id": 3, "value": str(random.randint(1, 3))},
        ],
    }, headers={"Authorization": f"Bearer {tokens[user_idx]}"})
    if resp.status_code == 200:
        sub_count += 1
log(f"  Created {sub_count} submissions")

# ── Warm-up ──
log("\nWarming up...")
for _ in range(5):
    idx = random.randint(0, len(tokens) - 1)
    client.get("/leaderboard", headers={"Authorization": f"Bearer {tokens[idx]}"})
    client.get("/me/dashboard", headers={"Authorization": f"Bearer {tokens[idx]}"})

# ── Measurements ──
log("\nMeasuring endpoint response times...\n")
samples = 20
results = {}

endpoints = [
    ("GET /health", "GET", "/health"),
    ("GET /metrics", "GET", "/metrics"),
    ("GET /leaderboard", "GET", "/leaderboard"),
    ("GET /quizzes (list)", "GET", "/quizzes"),
    ("GET /quizzes/search", "GET", "/quizzes/search?q=Perf+Quiz"),
]

for name, method, path in endpoints:
    times = []
    for s in range(min(samples, len(tokens))):
        idx = s % len(tokens)
        elapsed, status = time_endpoint(name, method, path,
                                        headers={"Authorization": f"Bearer {tokens[idx]}"})
        times.append(elapsed)
    avg = round(sum(times) / len(times), 1)
    results[name] = {
        "avg_ms": avg,
        "min_ms": min(times),
        "max_ms": max(times),
        "samples": len(times),
    }

# Auth-required endpoints with specific user
idx = 0
for name, method, path in [
    ("GET /me/dashboard", "GET", "/me/dashboard"),
    ("GET /me/stats", "GET", "/me/stats"),
    ("GET /me/submissions", "GET", "/me/submissions"),
    ("GET /admin/dashboard", "GET", "/admin/dashboard"),
    ("GET /admin/users", "GET", "/admin/users"),
]:
    elapsed, status = time_endpoint(name, method, path,
                                    headers={"Authorization": f"Bearer {tokens[idx]}"})
    if name not in results:
        results[name] = {"avg_ms": elapsed, "min_ms": elapsed, "max_ms": elapsed, "samples": 1}

# ── Report ──
log("=" * 60)
log("  PERFORMANCE REPORT")
log("=" * 60)
print(f"\n{'Endpoint':<35} {'Avg (ms)':<10} {'Min (ms)':<10} {'Max (ms)':<10} {'Samples':<8}")
print("-" * 73)
for name, data in sorted(results.items()):
    print(f"{name:<35} {data['avg_ms']:<10} {data['min_ms']:<10} {data['max_ms']:<10} {data['samples']:<8}")

log("\nCleanup: DROP DATABASE quizapp to reset.")
db.close()
