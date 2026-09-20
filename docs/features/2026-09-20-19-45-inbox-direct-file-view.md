---
type: Feature Specification
title: Direct file viewing from the inbox
description: Make file names the primary view affordance and render uploaded HTML directly as a full-page isolated document instead of nesting it in a second iframe viewer.
tags:
  - inbox
  - file-viewing
  - html
  - security
sources:
  - title: Current inbox application
    url: https://github.com/TheTeamRAH/inbox
  - title: Inbox dashboard feature
    url: https://github.com/TheTeamRAH/inbox
status: proposed
author: whose-footprints-are-these
---

# Context

The inbox table currently exposes a separate `View` link for every row. For uploaded HTML, `/files/<id>/view` returns an Inbox-owned wrapper containing an iframe, which then exposes an `Open raw page` link. This creates an unnecessary two-step flow and leaves the actual artifact in a small nested browsing surface.

# Goal

Make the stored file name the direct view affordance and make the existing view route render HTML artifacts as full-page documents while preserving isolation from the Inbox application and its data.

# Scope

- Replace the table's separate `View` action with a link on the file name.
- Keep `Download` and archive/unarchive actions unchanged.
- Keep direct rendering behavior for images and text files.
- Change HTML viewing from an iframe wrapper to direct response of the uploaded HTML document.
- Apply a restrictive response policy to direct HTML rendering.
- Retain the raw HTML route only if existing compatibility requires it; it must not be linked from the table.
- Update tests and documentation for the changed viewing behavior.

# Requirements

1. Each file name in the inbox table is an anchor to `/files/<id>/view`.
2. The table no longer renders a separate `View` action label.
3. `Download` and archive/unarchive controls remain available for every file.
4. Non-HTML files continue to render inline through `/files/<id>/view` using their stored MIME type.
5. HTML files requested through `/files/<id>/view` return the stored HTML bytes directly with `text/html` content type and inline disposition.
6. Direct HTML responses include a CSP sandbox with `allow-scripts` but without `allow-same-origin`.
7. Direct HTML responses block network and document escape paths by default:
   - `default-src 'none'`
   - inline styles allowed
   - data/blob images allowed
   - data fonts allowed
   - scripts allowed only as required for local artifact behavior
   - objects, forms, framing, and base URI changes disallowed
8. Direct HTML responses include `X-Content-Type-Options: nosniff` and `Content-Disposition: inline`.
9. The application must not expose Inbox cookies, local storage, or same-origin application data to uploaded HTML.
10. The existing `/files/<id>/raw-html` compatibility route may remain, but its security policy must be no less restrictive than the direct view route and it must not be required for normal viewing.
11. Existing upload, pagination, period filtering, download, archive, API, and retention behavior remains unchanged.

# Acceptance criteria

- A rendered inbox row contains a clickable filename linking to its view route.
- A rendered inbox row does not contain a separate `View` link.
- An HTML view response contains the uploaded HTML payload, not the old iframe wrapper or `Open raw page` text.
- An HTML view response has the expected restrictive CSP, `nosniff`, and inline disposition headers.
- The direct HTML response does not grant same-origin access.
- Image and text view tests continue to pass.
- Download and archive actions continue to work.
- The full test suite passes.

# Constraints

- Do not add a new dependency or database migration.
- Preserve server-rendered HTML and current route names.
- Do not weaken upload validation or expose runtime data.
- Keep the implementation compatible with the existing private-network deployment.

# Implementation notes

- Remove the obsolete wrapper template if no route needs it after the change.
- Reuse `require_item` so the direct path retains metadata and payload existence checks.
- Centralize the restrictive HTML response headers to avoid policy drift between `/view` and `/raw-html`.
- Use tests that assert response bytes and security headers rather than browser-specific iframe behavior.

# Risks and rollback

The main risk is that some uploaded prototypes depend on external resources or same-origin browser APIs; the restrictive policy intentionally prevents those dependencies. Users can still download the original file. Rollback is a single application commit reverting the direct HTML response and filename link.

# Validation

- Add or update Flask test-client coverage for filename links, removed View actions, direct HTML bytes, and security headers.
- `uv run pytest -q`
- `uv run python -m compileall -q src tests`
- `git diff --check`
