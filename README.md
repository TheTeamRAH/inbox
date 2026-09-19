# Inbox

A small private-network web application for uploading screenshots and other agentic-work artifacts from a phone, then retrieving them from the agentic environment.

The application is intended to run as its own Docker Compose stack, separate from the agentic stack:

- Compose project name: `inbox`
- Reverse-proxy name: `inbox.rah.home`
- Access control: the existing reverse-proxy restrictions are the initial security boundary
- Storage: persistent host-backed storage managed by configuration management
- Default retention: 60 days
- Archived files: retained indefinitely

Initial supported file classes:

- Images
- `.log`
- `.txt`
- `.html`

The application will not expose an MCP server in the initial release. Agents can retrieve files through the service API or a read-only shared storage mount, depending on the approved deployment design.

Implementation is pending review of the feature specification in `docs/features/2026-09-19-10-46-inbox-web-app.md`.
