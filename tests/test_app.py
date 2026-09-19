from io import BytesIO
from pathlib import Path

from inbox.app import create_app
from inbox.storage import cleanup_expired


def make_client(tmp_path: Path):
    app = create_app(
        {
            "DATABASE_PATH": str(tmp_path / "inbox.sqlite3"),
            "STORAGE_DIR": str(tmp_path / "files"),
            "RETENTION_DAYS": 60,
            "TIMEZONE": "Europe/London",
            "TESTING": True,
        }
    )
    return app.test_client(), app


def upload(client, filename: str, content: bytes, suffix: str):
    return client.post(
        "/upload",
        data={
            "suffix": suffix,
            "file": (BytesIO(content), filename),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )


def test_upload_lists_and_renders_supported_files(tmp_path):
    client, _ = make_client(tmp_path)

    response = upload(client, "mockup.html", b"<h1>Hello</h1>", "landing-page")

    assert response.status_code == 302
    listing = client.get("/")
    assert listing.status_code == 200
    assert b"landing-page.html" in listing.data

    file_id = listing.data.split(b"/files/")[1].split(b"/")[0].decode()
    rendered = client.get(f"/files/{file_id}/view")
    assert rendered.status_code == 200
    assert rendered.mimetype == "text/html"
    assert "Content-Security-Policy" in rendered.headers
    assert b"attachment" not in rendered.headers.get("Content-Disposition", "").lower().encode()
    assert b"html,body{width:100%;height:100%;margin:0;overflow:hidden}" in rendered.data
    assert b"Open raw page" in rendered.data

    download = client.get(f"/files/{file_id}/download")
    assert download.status_code == 200
    assert "attachment" in download.headers["Content-Disposition"]
    assert download.data == b"<h1>Hello</h1>"


def test_text_and_image_files_have_view_routes(tmp_path):
    client, _ = make_client(tmp_path)

    text_response = upload(client, "notes.log", b"one\ntwo\n", "run-log")
    assert text_response.status_code == 302
    image_response = upload(client, "pixel.png", b"fake-png", "pixel")
    assert image_response.status_code == 302

    listing = client.get("/api/files").get_json()
    assert len(listing) == 2
    by_name = {item["suffix"]: item for item in listing}

    text_view = client.get(f"/files/{by_name['run-log']['id']}/view")
    assert text_view.mimetype == "text/plain"
    assert b"one\ntwo" in text_view.data

    image_view = client.get(f"/files/{by_name['pixel']['id']}/view")
    assert image_view.status_code == 200
    assert image_view.mimetype == "image/png"


def test_archive_excludes_file_from_expiry_cleanup(tmp_path):
    client, app = make_client(tmp_path)
    response = upload(client, "keep.txt", b"keep", "important")
    assert response.status_code == 302
    item = client.get("/api/files").get_json()[0]

    assert client.post(f"/files/{item['id']}/archive").status_code == 302
    removed = cleanup_expired(app.config["DATABASE_PATH"], app.config["STORAGE_DIR"], age_days=-1)

    assert removed == 0
    assert client.get(f"/files/{item['id']}/download").status_code == 200


def test_rejects_unsupported_extensions(tmp_path):
    client, _ = make_client(tmp_path)

    response = upload(client, "run.sh", b"#!/bin/sh", "script")

    assert response.status_code == 400
    assert b"Unsupported file type" in response.data
    assert client.get("/api/files").get_json() == []
