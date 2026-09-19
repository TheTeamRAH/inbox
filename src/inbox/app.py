"""Flask web application for uploading and viewing files."""

from __future__ import annotations

import html
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    redirect,
    render_template_string,
    request,
    url_for,
)
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import RequestEntityTooLarge

from .storage import add_file, get_file, list_files, set_archived

ALLOWED_EXTENSIONS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".log": "text/plain",
    ".txt": "text/plain",
    ".html": "text/html",
    ".htm": "text/html",
}
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")

LIST_TEMPLATE = """
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inbox</title>
<style>body{font:16px system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}form{display:grid;gap:.6rem;margin-bottom:2rem}input,button{font:inherit;padding:.55rem}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #ddd;padding:.6rem .3rem}a{margin-right:.7rem}.muted{color:#666}</style></head>
<body>
<h1>Inbox</h1>
<form action="{{ url_for('upload') }}" method="post" enctype="multipart/form-data">
<label>File <input type="file" name="file" required></label>
<label>Name suffix <input name="suffix" placeholder="e.g. landing-page" required></label>
<button type="submit">Upload</button>
</form>
<nav><a href="{{ url_for('index') }}">All</a><a href="{{ url_for('index', period='today') }}">Today</a><a href="{{ url_for('index', period='week') }}">This week</a><a href="{{ url_for('index', period='month') }}">This month</a></nav>
{% if error %}<p role="alert">{{ error }}</p>{% endif %}
<table><thead><tr><th>File</th><th>Uploaded</th><th>Size</th><th>State</th><th>Actions</th></tr></thead><tbody>
{% for item in files %}<tr><td>{{ item.stored_name }}</td><td>{{ item.uploaded_at }}</td><td>{{ item.size }}</td><td>{{ 'Archived' if item.archived else 'Active' }}</td><td><a href="{{ url_for('view_file', file_id=item.id) }}">View</a><a href="{{ url_for('download_file', file_id=item.id) }}">Download</a><form style="display:inline" method="post" action="{{ url_for('archive_file', file_id=item.id) }}"><button>{{ 'Unarchive' if item.archived else 'Archive' }}</button></form></td></tr>{% endfor %}
</tbody></table>
</body></html>
"""

HTML_VIEW_TEMPLATE = """
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ name }}</title><style>body{margin:0}iframe{border:0;width:100vw;height:100vh}</style></head><body><iframe title="Uploaded HTML preview" sandbox="allow-scripts" src="{{ raw_url }}"></iframe></body></html>
"""


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the Inbox Flask application."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_PATH=os.environ.get("DATABASE_PATH", "data/inbox.sqlite3"),
        STORAGE_DIR=os.environ.get("STORAGE_DIR", "data/files"),
        RETENTION_DAYS=int(os.environ.get("RETENTION_DAYS", "60")),
        TIMEZONE=os.environ.get("TIMEZONE", "UTC"),
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024))),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["STORAGE_DIR"]).mkdir(parents=True, exist_ok=True)

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_: RequestEntityTooLarge):
        return "Upload is too large", 413

    @app.get("/")
    def index():
        period = request.args.get("period")
        if period not in {None, "today", "week", "month"}:
            period = None
        return render_template_string(LIST_TEMPLATE, files=list_files(app.config["DATABASE_PATH"], period, app.config["TIMEZONE"]), error=None)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/files")
    def api_files():
        period = request.args.get("period")
        return jsonify(list_files(app.config["DATABASE_PATH"], period, app.config["TIMEZONE"]))

    @app.post("/upload")
    def upload():
        uploaded: FileStorage | None = request.files.get("file")
        suffix = slugify(request.form.get("suffix", ""))
        if not uploaded or not uploaded.filename:
            return "A file is required", 400
        if not suffix:
            return "A name suffix is required", 400
        extension = Path(uploaded.filename).suffix.lower()
        mime_type = ALLOWED_EXTENSIONS.get(extension)
        if not mime_type:
            return "Unsupported file type", 400
        local_now = datetime.now(ZoneInfo(app.config["TIMEZONE"]))
        timestamp = local_now.strftime("%Y-%m-%d-%H-%M-%S")
        stored_name = f"{timestamp}-{suffix}{extension}"
        storage_dir = Path(app.config["STORAGE_DIR"])
        while (storage_dir / stored_name).exists():
            stored_name = f"{timestamp}-{suffix}-{uuid.uuid4().hex[:8]}{extension}"
        file_id = uuid.uuid4().hex
        path = storage_dir / stored_name
        uploaded.save(path)
        try:
            add_file(
                app.config["DATABASE_PATH"],
                {
                    "id": file_id,
                    "stored_name": stored_name,
                    "original_name": Path(uploaded.filename).name,
                    "suffix": suffix,
                    "mime_type": mime_type,
                    "size": path.stat().st_size,
                    "uploaded_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                },
            )
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return redirect(url_for("index"))

    @app.post("/files/<file_id>/archive")
    def archive_file(file_id: str):
        item = get_file(app.config["DATABASE_PATH"], file_id)
        if not item:
            abort(404)
        set_archived(app.config["DATABASE_PATH"], file_id, not bool(item["archived"]))
        return redirect(url_for("index"))

    @app.get("/files/<file_id>/view")
    def view_file(file_id: str):
        item = require_item(app, file_id)
        if item["mime_type"] == "text/html":
            response = Response(
                render_template_string(
                    HTML_VIEW_TEMPLATE,
                    name=html.escape(item["stored_name"]),
                    raw_url=url_for("raw_html", file_id=file_id),
                ),
                mimetype="text/html",
            )
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'"
            return response
        path = Path(app.config["STORAGE_DIR"]) / item["stored_name"]
        return Response(path.read_bytes(), mimetype=item["mime_type"])

    @app.get("/files/<file_id>/raw-html")
    def raw_html(file_id: str):
        item = require_item(app, file_id)
        if item["mime_type"] != "text/html":
            abort(404)
        path = Path(app.config["STORAGE_DIR"]) / item["stored_name"]
        response = Response(path.read_bytes(), mimetype="text/html")
        response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data: blob:; font-src data:; object-src 'none'; base-uri 'none'; form-action 'none'"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/files/<file_id>/download")
    def download_file(file_id: str):
        item = require_item(app, file_id)
        path = Path(app.config["STORAGE_DIR"]) / item["stored_name"]
        response = Response(path.read_bytes(), mimetype=item["mime_type"])
        response.headers["Content-Disposition"] = f'attachment; filename="{item["stored_name"]}"'
        return response

    return app


def require_item(app: Flask, file_id: str) -> dict[str, Any]:
    """Load a file record or abort with 404."""
    item = get_file(app.config["DATABASE_PATH"], file_id)
    if not item:
        abort(404)
    assert item is not None
    path = Path(app.config["STORAGE_DIR"]) / item["stored_name"]
    if not path.is_file():
        abort(404)
    return item


def slugify(value: str) -> str:
    """Convert a user-provided suffix into a safe lowercase filename fragment."""
    value = value.strip().lower()
    return SLUG_PATTERN.sub("-", value).strip("-")[:80]


def main() -> None:
    """Run the development server for local use."""
    create_app().run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8080")))
