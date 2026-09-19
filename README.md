# inbox

A separate Docker Compose web application for uploading and retrieving screenshots and small files through the restricted `inbox.rah.home` reverse-proxy endpoint for use by the agentic environment.

## Repo Structure

```text
.
├── .gitignore
├── AGENTS.md
├── README.md
└── docs/
    └── features/
        ├── README.md
        └── 2026-09-19-10-46-inbox-web-app.md
```

## Getting Started

Implementation is not started yet. Review the proposed [inbox web application specification](docs/features/2026-09-19-10-46-inbox-web-app.md) before adding application or Compose files.

Once implementation begins, setup and validation commands will be documented here only after they have been verified in this repository.

## Recent Features

| Date | Purpose | Spec | Author |
| --- | --- | --- | --- |

No implemented features are recorded yet.

See [all feature specifications](docs/features/README.md).

## Contributing

This is an AI-first development repository. Point your agent or model at [AGENTS.md](AGENTS.md) before contributing.

- Create and have a feature specification reviewed before implementation; create the required branch only when asked to continue.
- Follow the `docs/` structure, timestamped filename rules, and OKF documentation requirements in `AGENTS.md`.
- Consult discovery documentation before related work and keep reusable lessons current.
- Use test-driven development for code, keep the reverse-proxy and persistent-storage boundaries explicit, and do not add secrets or uploaded runtime data to this public repository.
- Keep communication concise, source factual claims, and ask when requirements are unclear.
