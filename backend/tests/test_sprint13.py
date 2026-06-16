import pytest
import re


# ── 1. Password Reset — token não exposto em logs ──

def test_password_reset_token_not_in_logs(client, db_session, caplog):
    """Verifica que o token bruto de reset de senha não aparece nos logs."""
    from database import UserDB
    import logging
    caplog.set_level(logging.INFO)

    client.post("/auth/register", json={
        "name": "Log Test", "email": "logtest@example.com", "password": "password123",
    })

    user = db_session.query(UserDB).filter(UserDB.email == "logtest@example.com").first()
    assert user is not None

    # Limpa logs do registro
    caplog.clear()

    resp = client.post("/auth/forgot-password", json={"email": "logtest@example.com"})
    assert resp.status_code == 200

    # Verifica que nenhum log contém uma string hex longa (token)
    for record in caplog.records:
        message = record.getMessage()
        # Procura por strings hex de 64+ caracteres (tamanho do token)
        hex_pattern = r'[0-9a-f]{64,}'
        matches = re.findall(hex_pattern, message)
        assert len(matches) == 0, f"Token hex encontrado no log: {matches[0]}"


# ── 2. Root redirect ──

def test_root_redirects_to_index(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/static/index.html"


# ── 3. Update quiz description ──

def test_update_quiz_description(client, auth_headers, created_quiz):
    new_desc = "Descrição atualizada"
    resp = client.put(f"/quizzes/{created_quiz['id']}", json={
        "description": new_desc,
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["description"] == new_desc


# ── 4. Update quiz questions ──

def test_update_quiz_questions(client, auth_headers, created_quiz):
    new_questions = [
        {"id": 1, "text": "Nova pergunta?", "type": "text", "required": True},
        {"id": 2, "text": "Escolha:", "type": "single_choice", "required": True,
         "options": [{"id": 1, "text": "Opção A"}, {"id": 2, "text": "Opção B"}]},
    ]
    resp = client.put(f"/quizzes/{created_quiz['id']}", json={
        "questions": new_questions,
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["questions"]) == 2
    assert resp.json()["questions"][0]["text"] == "Nova pergunta?"


# ── 5. Update category ──

def test_update_quiz_category(client, auth_headers, created_quiz, db_session):
    from database import CategoryDB
    cat = CategoryDB(name="Ciência", slug="ciencia")
    db_session.add(cat)
    db_session.commit()

    resp = client.put(f"/quizzes/{created_quiz['id']}", json={
        "category_id": cat.id,
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["category"] is not None
    assert resp.json()["category"]["name"] == "Ciência"


def test_update_quiz_category_not_found(client, auth_headers, created_quiz):
    resp = client.put(f"/quizzes/{created_quiz['id']}", json={
        "category_id": 99999,
    }, headers=auth_headers)
    assert resp.status_code == 400


# ── 6. Update tags ──

def test_update_quiz_tags(client, auth_headers, created_quiz, db_session):
    from database import TagDB
    tag1 = TagDB(name="python")
    tag2 = TagDB(name="web")
    db_session.add_all([tag1, tag2])
    db_session.commit()

    resp = client.put(f"/quizzes/{created_quiz['id']}", json={
        "tag_ids": [tag1.id, tag2.id],
    }, headers=auth_headers)
    assert resp.status_code == 200
    tag_names = [t["name"] for t in resp.json()["tags"]]
    assert "python" in tag_names
    assert "web" in tag_names


# ── 7. Admin role — user not found ──

def test_admin_set_role_user_not_found(client):
    client.post("/auth/register", json={
        "name": "Admin", "email": "test@example.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = client.put("/admin/users/99999/role", json={"role": "admin"},
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


# ── 8. Password >72 bytes ──

def test_password_over_72_bytes_raises_error(client):
    """bcrypt tem limite de 72 bytes. O hash_password deve lançar ValueError."""
    from auth import hash_password
    long_password = "a" * 73
    with pytest.raises(ValueError, match="Password exceeds bcrypt 72-byte limit"):
        hash_password(long_password)


# ── 9. Creator badge ──

def test_badges_creator(client, auth_headers, created_quiz):
    me = client.get("/auth/me", headers=auth_headers).json()
    resp = client.get(f"/users/{me['id']}/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    names = [b["name"] for b in data["badges"]]
    assert "Criador" in names


# ── 10. Regular user cannot create quiz ──

def test_regular_user_cannot_create_quiz(client):
    # Register a non-admin user
    resp = client.post("/auth/register", json={
        "name": "Regular User", "email": "regular@example.com", "password": "password123",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp = client.post("/quizzes", json={
        "title": "Should Fail", "description": "",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ── 11. Regular user cannot update quiz ──

def test_regular_user_cannot_update_quiz(client, auth_headers, created_quiz):
    # User B is also admin in test config, so create a truly regular user
    resp = client.post("/auth/register", json={
        "name": "Regular User", "email": "regular2@example.com", "password": "password123",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp = client.put(f"/quizzes/{created_quiz['id']}", json={"title": "Hacked"},
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ── 12. Regular user cannot delete quiz ──

def test_regular_user_cannot_delete_quiz(client, auth_headers, created_quiz):
    resp = client.post("/auth/register", json={
        "name": "Regular User", "email": "regular3@example.com", "password": "password123",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp = client.delete(f"/quizzes/{created_quiz['id']}",
                         headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ── 13. Health check database ──

def test_health_database_status(client):
    resp = client.get("/health/database")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


# ── 14. Leaderboard requires auth ──

def test_leaderboard_requires_auth(client):
    resp = client.get("/leaderboard")
    assert resp.status_code == 401


# ── 15. Quiz leaderboard requires auth ──

def test_quiz_leaderboard_requires_auth(client):
    resp = client.get("/quizzes/1/leaderboard")
    assert resp.status_code == 401
