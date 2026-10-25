def create_user(client, name, email):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "Correct-Horse-Battery!47"},
    )
    assert response.status_code == 201


def login(client, email):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Correct-Horse-Battery!47"},
    )
    assert response.status_code == 200
    return client.cookies.get("csrf_token")


def test_registration_login_and_duplicate_rejection(client):
    create_user(client, "Avery", "avery@example.com")
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"name": "Another", "email": "avery@example.com", "password": "Correct-Horse-Battery!47"},
    )
    assert duplicate.status_code == 409
    login(client, "avery@example.com")
    assert client.get("/api/v1/auth/me").json()["name"] == "Avery"
    invalid = client.post(
        "/api/v1/auth/login",
        json={"email": "avery@example.com", "password": "incorrect-password"},
    )
    assert invalid.status_code == 401


def test_file_isolation_and_csrf(client):
    create_user(client, "Avery", "avery@example.com")
    token_a = login(client, "avery@example.com")
    upload = client.post(
        "/api/v1/files",
        files={"file": ("private.txt", b"private A", "text/plain")},
        headers={"X-CSRF-Token": token_a},
    )
    assert upload.status_code == 201
    file_id = upload.json()["id"]
    downloaded = client.get(f"/api/v1/files/{file_id}/download")
    assert downloaded.status_code == 200
    assert downloaded.content == b"private A"
    assert downloaded.headers["content-disposition"].startswith("attachment;")
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token_a})

    create_user(client, "Blake", "blake@example.com")
    login(client, "blake@example.com")
    assert client.get("/api/v1/files").json() == []
    assert client.get(f"/api/v1/files/{file_id}/download").status_code == 404
    assert client.delete(
        f"/api/v1/files/{file_id}", headers={"X-CSRF-Token": client.cookies.get("csrf_token")}
    ).status_code == 404


def test_upload_quota_and_trash_restore(client, monkeypatch):
    create_user(client, "Avery", "avery@example.com")
    csrf = login(client, "avery@example.com")
    monkeypatch.setattr("app.main.settings.max_upload_bytes", 4)
    response = client.post(
        "/api/v1/files",
        files={"file": ("too-large.txt", b"12345", "text/plain")},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 413
    monkeypatch.setattr("app.main.settings.max_upload_bytes", 10)
    uploaded = client.post(
        "/api/v1/files",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers={"X-CSRF-Token": csrf},
    )
    assert uploaded.status_code == 201
    item_id = uploaded.json()["id"]
    assert client.get("/api/v1/dashboard").json()["used_bytes"] == 5
    assert client.delete(f"/api/v1/files/{item_id}", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert client.get("/api/v1/dashboard").json()["used_bytes"] == 0
    assert client.post(f"/api/v1/files/{item_id}/restore", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert client.get("/api/v1/dashboard").json()["used_bytes"] == 5


def test_upload_is_rejected_when_user_quota_is_exceeded(client, monkeypatch):
    from app.main import settings

    monkeypatch.setattr(settings, "default_quota_bytes", 4)
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    create_user(client, "Avery", "avery@example.com")
    csrf = login(client, "avery@example.com")
    response = client.post(
        "/api/v1/files",
        files={"file": ("too-large-for-quota.txt", b"12345", "text/plain")},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "Storage quota exceeded"


def test_mutations_require_csrf(client):
    create_user(client, "Avery", "avery@example.com")
    login(client, "avery@example.com")
    result = client.post("/api/v1/folders", json={"name": "Personal"})
    assert result.status_code == 403


def test_profile_information_can_be_updated_and_email_must_be_unique(client):
    create_user(client, "Avery", "avery@example.com")
    csrf = login(client, "avery@example.com")
    create_user(client, "Blake", "blake@example.com")

    updated = client.patch(
        "/api/v1/profile",
        json={"name": "Avery Quinn", "email": "avery.new@example.com", "phone": "+1 555 010 2345"},
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Avery Quinn"
    assert updated.json()["email"] == "avery.new@example.com"
    assert updated.json()["phone"] == "+1 555 010 2345"

    duplicate = client.patch(
        "/api/v1/profile",
        json={"name": "Avery Quinn", "email": "blake@example.com", "phone": ""},
        headers={"X-CSRF-Token": csrf},
    )
    assert duplicate.status_code == 409


def test_profile_photo_upload_is_private_and_removable(client):
    create_user(client, "Avery", "avery@example.com")
    csrf = login(client, "avery@example.com")
    png = b"\x89PNG\r\n\x1a\n" + b"sample-image-data"
    uploaded = client.post(
        "/api/v1/profile/avatar",
        files={"file": ("avatar.png", png, "text/plain")},
        headers={"X-CSRF-Token": csrf},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["avatar_url"] == "/api/v1/profile/avatar"
    photo = client.get("/api/v1/profile/avatar")
    assert photo.status_code == 200
    assert photo.content == png
    assert photo.headers["content-type"] == "image/png"
    assert photo.headers["content-disposition"] == "inline"

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert client.get("/api/v1/profile/avatar").status_code == 401
    create_user(client, "Blake", "blake@example.com")
    login(client, "blake@example.com")
    assert client.get("/api/v1/profile/avatar").status_code == 404

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("csrf_token")})
    login(client, "avery@example.com")
    csrf = client.cookies.get("csrf_token")
    removed = client.delete(
        "/api/v1/profile/avatar", headers={"X-CSRF-Token": csrf}
    )
    assert removed.status_code == 200
    assert removed.json()["avatar_url"] is None
    assert client.get("/api/v1/profile/avatar").status_code == 404


def test_profile_photo_rejects_non_image_content(client):
    create_user(client, "Avery", "avery@example.com")
    csrf = login(client, "avery@example.com")
    response = client.post(
        "/api/v1/profile/avatar",
        files={"file": ("avatar.jpg", b"not-an-image", "image/jpeg")},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 415


def test_production_login_cookies_are_cross_site_secure(client, monkeypatch):
    from app.main import settings

    monkeypatch.setattr(settings, "session_cookie_secure", True)
    monkeypatch.setattr(settings, "session_cookie_samesite", "none")
    create_user(client, "Avery", "avery@example.com")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "avery@example.com", "password": "Correct-Horse-Battery!47"},
    )
    assert response.status_code == 200
    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(cookie.lower() for cookie in cookies if cookie.startswith("session="))
    csrf_cookie = next(cookie.lower() for cookie in cookies if cookie.startswith("csrf_token="))
    assert "httponly" in session_cookie
    assert "secure" in session_cookie
    assert "samesite=none" in session_cookie
    assert "secure" in csrf_cookie
    assert "samesite=none" in csrf_cookie
