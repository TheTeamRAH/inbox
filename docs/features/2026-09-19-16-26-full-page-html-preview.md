---
type: Feature
title: Full-page HTML preview
status: completed
description: Render uploaded static HTML pages as a usable full-page preview while retaining isolation and a separate download path.
tags:
  - html
  - preview
  - security
sources:
  - title: Inbox application implementation
    path: src/inbox/app.py
  - title: Inbox application tests
    path: tests/test_app.py
---

# Full-page HTML preview

## Context

The current HTML preview route returns a wrapper document containing a sandboxed
iframe. In the deployed application, this makes static pages difficult to review
and gives users no explicit way to open the raw rendered page directly. The
separate download route must continue returning the original file as an
attachment.

## Goal

Make HTML previews usable for reviewing static web pages at the full available
viewport while preserving the existing isolation and download behavior.

## Requirements

- `GET /files/<id>/view` renders an HTML preview page occupying the available
  viewport without relying on intrinsic iframe sizing.
- The preview provides an explicit link to open the raw rendered HTML page.
- The raw HTML response remains isolated with a restrictive Content-Security-
  Policy and does not become a download.
- The download route remains a separate attachment response with unchanged bytes.
- Non-HTML view behavior remains unchanged.
- Existing HTML preview security tests remain valid, with regression coverage for
  the full-page wrapper contract and raw-page link.

## Out of scope

- Allowing external network requests, forms, plugins, or top-level navigation from
  uploaded HTML.
- Rewriting uploaded HTML or its CSS.
- Changing retention, upload, metadata, or archive behavior.

## Acceptance criteria

- The generated preview wrapper sets explicit dimensions on `html`, `body`, and
  the preview surface and removes default page margins/overflow that can shrink or
  constrain the review area.
- The wrapper includes a visible raw-page link.
- Tests pass for HTML preview, raw HTML security headers, download attachment
  behavior, and the complete application suite.
- `git diff --check` passes.

## Lifecycle

This specification is completed. The full-page preview wrapper is implemented,
validated, and included in the Inbox delivery branch. The deployed HTML endpoint
was read back and verified to return the isolated preview wrapper and raw HTML
routes.
