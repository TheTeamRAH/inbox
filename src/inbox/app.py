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
PAGE_SIZES = (8, 16, 32, 64)

LIST_TEMPLATE = """
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inbox</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#172033;background:#eef2f7}*{box-sizing:border-box}body{margin:0}.page{max-width:1180px;margin:0 auto;padding:2.5rem 1.25rem 4rem}h1{font-size:2.2rem;letter-spacing:-.04em;margin:0}.muted{color:#68758a}.subtitle{margin:.35rem 0 1.6rem;color:#68758a}.upload{display:grid;grid-template-columns:1fr 220px auto;gap:.75rem;align-items:center;padding:1rem;background:#fff;border:1px solid #d7dfeb;border-radius:.75rem;box-shadow:0 8px 24px #23364b10}.upload label{font-size:.8rem;color:#68758a}.upload input{display:block;width:100%;font:inherit;margin-top:.25rem;padding:.6rem;border:1px solid #cbd4e1;border-radius:.45rem;background:#fff}.upload button,.page-size button{font:inherit;cursor:pointer;border:0;border-radius:.45rem;background:#2364c4;color:#fff;padding:.65rem 1rem}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin:1.25rem 0}.metric{background:#fff;border:1px solid #d7dfeb;border-radius:.65rem;padding:1rem}.metric strong{display:block;font-size:1.7rem;letter-spacing:-.03em}.metric span{font-size:.8rem;color:#68758a}.filters{display:flex;gap:1rem;align-items:center;flex-wrap:wrap;margin:1.1rem 0}.filters a{color:#68758a;text-decoration:none}.filters a.active{color:#2364c4;font-weight:700;border-bottom:2px solid #2364c4;padding-bottom:.35rem}.page-size{margin-left:auto;display:flex;gap:.5rem;align-items:center;color:#68758a;font-size:.85rem}.page-size select{font:inherit;padding:.45rem;border:1px solid #cbd4e1;border-radius:.4rem;background:#fff;color:#172033}.table-wrap{overflow-x:auto;border:1px solid #d7dfeb;border-radius:.75rem;background:#fff}.file-table{width:100%;border-collapse:collapse;min-width:760px;font-size:.85rem}.file-table th{background:#f6f8fb;color:#68758a;text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em}.file-table th,.file-table td{padding:.85rem;border-bottom:1px solid #e7ecf2;vertical-align:middle}.file-table tr:last-child td{border-bottom:0}.file-table td:first-child{font-weight:650;color:#1e4f9a;overflow-wrap:anywhere}.file-table td:nth-child(2),.file-table td:nth-child(3){white-space:nowrap;color:#68758a}.state{color:#207a4a}.state:before{content:'';display:inline-block;width:.42rem;height:.42rem;margin-right:.35rem;border-radius:50%;background:#36b56d}.actions{white-space:nowrap}.actions a{color:#2364c4;margin-right:.7rem}.actions form{display:inline}.actions button{font:inherit;padding:.4rem .55rem;border:1px solid #b8c4d4;border-radius:.35rem;background:#f8fafc;color:#46546a;cursor:pointer}.pagination{display:flex;justify-content:space-between;align-items:center;gap:1rem;margin-top:1rem;color:#68758a;font-size:.85rem}.pagination a{color:#2364c4;text-decoration:none}.pagination .pages{display:flex;gap:.35rem;align-items:center}.pagination .pages a{border:1px solid #cbd4e1;background:#fff;border-radius:.35rem;padding:.4rem .6rem}.pagination .pages a.active{background:#2364c4;border-color:#2364c4;color:#fff}.error{padding:.75rem;background:#fff0f0;color:#a32929;border:1px solid #f0b6b6;border-radius:.5rem}.empty{padding:2rem;text-align:center;color:#68758a}
@media(max-width:700px){.page{padding:1.25rem .75rem 3rem}.upload{grid-template-columns:1fr}.metrics{grid-template-columns:1fr}.page-size{margin-left:0}.pagination{align-items:flex-start;flex-direction:column}}
</style></head>
<body>
<main class="page"><h1>Inbox</h1><p class="subtitle">Upload and manage your generated artifacts.</p>
<form class="upload" action="{{ url_for('upload') }}" method="post" enctype="multipart/form-data"><label>File<input type="file" name="file" required></label><label>Name suffix<input name="suffix" placeholder="e.g. landing-page" required></label><button type="submit">Upload</button></form>
{% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
<section class="metrics" aria-label="Inbox summary"><div class="metric"><strong>{{ total_files }}</strong><span>Total files</span></div><div class="metric"><strong>{{ active_files }}</strong><span>Active files</span></div><div class="metric"><strong>{{ archived_files }}</strong><span>Archived files</span></div></section>
<nav class="filters" aria-label="File date filters"><a class="{{ 'active' if not period else '' }}" href="{{ url_for('index', per_page=per_page) }}">All</a><a class="{{ 'active' if period == 'today' else '' }}" href="{{ url_for('index', period='today', per_page=per_page) }}">Today</a><a class="{{ 'active' if period == 'week' else '' }}" href="{{ url_for('index', period='week', per_page=per_page) }}">This week</a><a class="{{ 'active' if period == 'month' else '' }}" href="{{ url_for('index', period='month', per_page=per_page) }}">This month</a><form class="page-size" method="get" action="{{ url_for('index') }}"><input type="hidden" name="period" value="{{ period or '' }}"><label for="per-page">Rows per page</label><select id="per-page" name="per_page" onchange="this.form.submit()">{% for size in page_sizes %}<option value="{{ size }}"{{ ' selected' if size == per_page else '' }}>{{ size }}</option>{% endfor %}</select></form></nav>
<div class="table-wrap"><table class="file-table"><thead><tr><th>File</th><th>Uploaded</th><th>Size</th><th>State</th><th>Actions</th></tr></thead><tbody>
{% for item in files %}<tr><td>{{ item.stored_name }}</td><td>{{ item.uploaded_at }}</td><td>{{ item.size }}</td><td><span class="state">{{ 'Archived' if item.archived else 'Active' }}</span></td><td class="actions"><a href="{{ url_for('view_file', file_id=item.id) }}">View</a><a href="{{ url_for('download_file', file_id=item.id) }}">Download</a><form method="post" action="{{ url_for('archive_file', file_id=item.id) }}"><button>{{ 'Unarchive' if item.archived else 'Archive' }}</button></form></td></tr>{% else %}<tr><td class="empty" colspan="5">No files match this filter.</td></tr>{% endfor %}
</tbody></table></div>
<nav class="pagination" aria-label="Pagination"><span>Showing {{ start_index }}–{{ end_index }} of {{ total_files }} files</span><span class="pages">{% if page > 1 %}<a href="{{ url_for('index', period=period, page=page - 1, per_page=per_page) }}">Previous</a>{% endif %}{% for page_number in range(1, page_count + 1) %}<a class="{{ 'active' if page_number == page else '' }}" href="{{ url_for('index', period=period, page=page_number, per_page=per_page) }}">{{ page_number }}</a>{% endfor %}{% if page < page_count %}<a href="{{ url_for('index', period=period, page=page + 1, per_page=per_page) }}">Next</a>{% endif %}</span></nav></main>
</body></html>
"""

HTML_VIEW_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ name }}</title>
<style>
html,body{width:100%;height:100%;margin:0;overflow:hidden}
iframe{display:block;border:0;width:100%;height:100%}
.raw-link{position:fixed;top:.75rem;right:.75rem;z-index:1;padding:.45rem .7rem;border-radius:.4rem;background:#111c;color:#fff;font:14px system-ui,sans-serif}
</style>
</head>
<body>
<a class="raw-link" href="{{ raw_url }}" target="_blank" rel="noopener">Open raw page</a>
<iframe title="Uploaded HTML preview" sandbox="allow-scripts" src="{{ raw_url }}"></iframe>
</body>
</html>
"""


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Inbox Flask application.

    Args:
        test_config: Optional configuration overrides applied after environment
            defaults. Tests commonly provide temporary database and storage
            paths here.

    Returns:
        A configured Flask application with upload, listing, viewing, download,
        archive, and health routes.

    Examples:
        >>> app = create_app({"TESTING": True, "DATABASE_PATH": "/tmp/inbox.sqlite3", "STORAGE_DIR": "/tmp/inbox-files"})
        >>> app.config["TESTING"]
        True
    """
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
    def too_large(_: RequestEntityTooLarge) -> tuple[str, int]:
        """Return a stable response when an upload exceeds the size limit.

        Args:
            _: Flask's request-size exception. Its details are intentionally not
                exposed to the client.

        Returns:
            A plain-text error response and HTTP 413 status.

        Examples:
            A request larger than ``MAX_CONTENT_LENGTH`` receives
            ``("Upload is too large", 413)``.
        """
        return "Upload is too large", 413

    @app.get("/")
    def index() -> str:
        """Render the dashboard and paginated file listing.

        Returns:
            The upload form, filtered summary cards, and a server-rendered page
            of the file listing. Page sizes are constrained to ``PAGE_SIZES``.

        Examples:
            ``GET /?period=today&per_page=16&page=2`` renders the second page
            of today's files with sixteen rows per page.
        """
        period = request.args.get("period")
        if period not in {None, "today", "week", "month"}:
            period = None
        try:
            per_page = int(request.args.get("per_page", PAGE_SIZES[0]))
        except (TypeError, ValueError):
            per_page = PAGE_SIZES[0]
        if per_page not in PAGE_SIZES:
            per_page = PAGE_SIZES[0]
        try:
            requested_page = int(request.args.get("page", 1))
        except (TypeError, ValueError):
            requested_page = 1

        all_files = list_files(app.config["DATABASE_PATH"], period, app.config["TIMEZONE"])
        total_files = len(all_files)
        page_count = max(1, (total_files + per_page - 1) // per_page)
        page = min(max(requested_page, 1), page_count)
        start = (page - 1) * per_page
        page_files = all_files[start : start + per_page]
        return render_template_string(
            LIST_TEMPLATE,
            files=page_files,
            error=None,
            period=period,
            page=page,
            page_count=page_count,
            per_page=per_page,
            page_sizes=PAGE_SIZES,
            total_files=total_files,
            active_files=sum(not bool(item["archived"]) for item in all_files),
            archived_files=sum(bool(item["archived"]) for item in all_files),
            start_index=start + 1 if total_files else 0,
            end_index=min(start + per_page, total_files),
        )

    @app.get("/health")
    def health() -> Response:
        """Report that the application process is responding.

        Returns:
            JSON object with ``status`` set to ``"ok"`` and HTTP 200.

        Examples:
            ``GET /health`` returns ``{"status": "ok"}``.
        """
        return jsonify(status="ok")

    @app.get("/api/files")
    def api_files():
        """Return file metadata as JSON, optionally filtered by period.

        Returns:
            JSON array of file metadata dictionaries sorted newest first.

        Examples:
            ``GET /api/files?period=week`` returns the files uploaded during the
            current configured calendar week.
        """
        period = request.args.get("period")
        return jsonify(list_files(app.config["DATABASE_PATH"], period, app.config["TIMEZONE"]))

    @app.post("/upload")
    def upload():
        """Validate, persist, and register one multipart file upload.

        Returns:
            HTTP 302 redirect to the listing on success, or HTTP 400/413 for
            invalid or oversized input.

        Examples:
            A multipart request containing ``file=screen.png`` and
            ``suffix=router-status`` creates a name such as
            ``2026-09-19-12-00-00-router-status.png`` and redirects to ``/``.
        """
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
        """Toggle the archive state for a stored file.

        Args:
            file_id: Opaque ID from the file listing or API response.

        Returns:
            HTTP 302 redirect to the listing, or HTTP 404 if the file is absent.

        Examples:
            ``POST /files/abc123/archive`` changes an active file to archived,
            and a second request changes it back to active.
        """
        item = get_file(app.config["DATABASE_PATH"], file_id)
        if not item:
            abort(404)
        set_archived(app.config["DATABASE_PATH"], file_id, not bool(item["archived"]))
        return redirect(url_for("index"))

    @app.get("/files/<file_id>/view")
    def view_file(file_id: str):
        """Render a stored file inline or load its isolated HTML viewer.

        Args:
            file_id: Opaque ID from the file listing or API response.

        Returns:
            An inline response using the stored MIME type, or a sandboxed HTML
            viewer for uploaded HTML documents.

        Examples:
            ``GET /files/abc123/view`` renders a PNG as an image and wraps an
            HTML upload in the restricted viewer page.
        """
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
        """Serve an uploaded HTML document inside the restricted viewer.

        Args:
            file_id: Opaque ID of an uploaded HTML file.

        Returns:
            HTML content with a restrictive CSP, or HTTP 404 for non-HTML and
            missing files.

        Examples:
            ``GET /files/abc123/raw-html`` returns ``text/html`` without an
            attachment disposition so the iframe can render it.
        """
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
        """Return a stored file as a download attachment.

        Args:
            file_id: Opaque ID from the file listing or API response.

        Returns:
            The exact stored payload with its generated filename in the
            ``Content-Disposition`` header, or HTTP 404 when absent.

        Examples:
            ``GET /files/abc123/download`` returns the original bytes with
            ``Content-Disposition: attachment``.
        """
        item = require_item(app, file_id)
        path = Path(app.config["STORAGE_DIR"]) / item["stored_name"]
        response = Response(path.read_bytes(), mimetype=item["mime_type"])
        response.headers["Content-Disposition"] = f'attachment; filename="{item["stored_name"]}"'
        return response

    return app


def require_item(app: Flask, file_id: str) -> dict[str, Any]:
    """Load metadata and verify that the corresponding payload exists.

    Args:
        app: Flask application containing ``DATABASE_PATH`` and ``STORAGE_DIR``.
        file_id: Opaque ID assigned to the uploaded file.

    Returns:
        The file metadata dictionary when both metadata and payload exist.

    Raises:
        werkzeug.exceptions.NotFound: If metadata or the payload is missing.

    Examples:
        ``require_item(app, "abc123")`` returns a metadata dictionary such as
        ``{"stored_name": "2026-note.txt", "mime_type": "text/plain"}``.
    """
    item = get_file(app.config["DATABASE_PATH"], file_id)
    if not item:
        abort(404)
    assert item is not None
    path = Path(app.config["STORAGE_DIR"]) / item["stored_name"]
    if not path.is_file():
        abort(404)
    return item


def slugify(value: str) -> str:
    """Convert a user-provided suffix into a safe filename fragment.

    Args:
        value: Free-form suffix supplied by the uploader.

    Returns:
        Lowercase ASCII-safe text with runs of punctuation replaced by a
        hyphen, trimmed to 80 characters.

    Examples:
        >>> slugify(" Router status / evening ")
        'router-status-evening'
        >>> slugify("!!!")
        ''
    """
    value = value.strip().lower()
    return SLUG_PATTERN.sub("-", value).strip("-")[:80]


def main() -> None:
    """Run the development server for local use.

    Configuration is read from ``HOST`` and ``PORT`` environment variables.
    Production deployments should use the container's Gunicorn command instead.

    Examples:
        ``PORT=9000 uv run inbox`` starts the development server on port 9000.
    """
    create_app().run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8080")))
