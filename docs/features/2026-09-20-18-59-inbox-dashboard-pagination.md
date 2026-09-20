---
type: Feature Specification
title: Inbox dashboard with configurable pagination
description: Replace the basic inbox listing presentation with a dashboard-style summary and paginated file table while preserving the existing upload, filtering, viewing, downloading, and archive workflows.
tags:
  - inbox
  - dashboard
  - pagination
  - web-ui
sources:
  - title: Current inbox application
    url: https://github.com/TheTeamRAH/inbox
  - title: TheTeamRah inbox visual reference
    url: https://github.com/TheTeamRAH/inbox
status: proposed
author: whose-footprints-are-these
---

# Context

The current Flask inbox renders a functional but very basic upload form and unpaginated file table in `src/inbox/app.py`. The chosen redesign direction is the “At-a-glance dashboard” concept from the Lavish review board. The dashboard should improve visual hierarchy without changing the underlying file-management behavior.

# Goal

Make the inbox easier to scan and operate by adding a dashboard header with useful file totals, a polished upload area, and a paginated file table. The default page size must be eight items, with a user-selectable larger page size.

# Scope

- Add a dashboard-style presentation to the HTML inbox route.
- Show total files and useful status summaries at the top.
- Remove “Pending actions”; the current application has no pending-action workflow and the metric would be misleading.
- Add server-side pagination to the HTML listing.
- Default to eight items per page and allow the user to choose a larger page size.
- Preserve upload, period filters, view, download, archive/unarchive, error, and existing API behavior.
- Add focused tests for pagination, page-size validation, filter interaction, and dashboard status values.

# Requirements

1. The page title remains `Inbox`.
2. The upload form retains a file input, required name suffix, and `Upload` submit action.
3. Period filters remain available for `All`, `Today`, `This week`, and `This month`.
4. The listing remains a table with `File`, `Uploaded`, `Size`, `State`, and `Actions` columns.
5. Actions remain `View`, `Download`, and archive/unarchive.
6. The HTML listing accepts `page` and `per_page` query parameters.
7. `per_page` defaults to `8` when omitted.
8. Supported page sizes are 8, 16, 32, and 64; unsupported, non-integer, zero, or negative values fall back to 8.
9. Page numbers below 1 and pages past the last page resolve safely to the nearest valid page; an empty result set reports page 1 of 1.
10. Pagination links preserve the active period filter and selected page size.
11. The dashboard summary shows:
    - Total files: count of files matching the active period filter.
    - Active files: count of matching non-archived files.
    - Archived files: count of matching archived files.
12. Do not show a pending-actions metric because no corresponding domain state exists.
13. The page-size control visibly reports the current selection and offers 8, 16, 32, and 64.
14. The JSON `/api/files` response remains backward compatible and unpaginated unless pagination is explicitly added in a separate change.
15. Existing routes and storage behavior remain unchanged.

# Acceptance criteria

- A default `GET /` renders at most 8 file rows and shows the page-size control set to 8.
- `GET /?per_page=16` renders at most 16 rows and preserves `per_page=16` in pagination links.
- `GET /?per_page=bogus` behaves as `per_page=8`.
- `GET /?page=2&per_page=8` renders the second page in newest-first order.
- Period filters and pagination can be combined without losing either query parameter.
- Dashboard totals match the filtered dataset, including archived state.
- Existing upload, view, download, archive, API, and current tests continue to pass.
- No “Pending actions” label remains in the production inbox page.
- The page remains usable on narrow screens without horizontal overflow outside the table's intentional scroll container.

# Constraints

- Keep the application dependency-free beyond the existing Flask stack.
- Keep the current storage schema and route contracts unchanged.
- Use server-rendered HTML consistent with the existing application architecture.
- Do not include generated runtime data or secrets in the commit.

# Implementation notes

- Extend the storage listing path with a small reusable pagination/count helper or paginate the already filtered metadata in the app layer if that avoids a schema change.
- Keep filter semantics in the existing configured application timezone.
- Use escaped Jinja output and explicit query-string construction for pagination links.
- Prefer semantic controls and a native select for page size.

# Risks and rollback

The main risk is an incorrect count/page boundary or query-string combination. Tests should cover empty, exact-boundary, and out-of-range pages. Rollback is a single revert of the UI and pagination commit; no database migration is required.

# Validation

- `uv run pytest`
- Add targeted Flask test-client coverage for default and selectable pagination, invalid values, filter preservation, and summary counts.
- Inspect the rendered HTML for the absence of “Pending actions” and presence of the four supported page-size options.
- Run `git diff --check`.
