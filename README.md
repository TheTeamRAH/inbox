# inbox

A lightweight web application for uploading, organising, retaining, and retrieving screenshots and small files. It is designed to be useful as a self-hosted service or as a component of a larger deployment.

## Repo Structure

```text
.
├── .gitignore
├── AGENTS.md
├── Dockerfile
├── README.md
├── compose.example.yml
├── docs/
│   └── features/
│       ├── README.md
│       └── 2026-09-19-10-46-inbox-web-app.md
├── pyproject.toml
├── src/
│   └── inbox/
└── tests/
    └── test_app.py
```

## Getting Started

Implementation is in progress. For local development, install the project in an isolated environment and run the tests:

```bash
uv sync
uv run pytest
```

Run the development server with:

```bash
uv run inbox
```

The optional [Compose example](compose.example.yml) runs the application on port `8080` with persistent state under `./data`. Adapt it for the deployment environment rather than treating it as a required installation method.

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
- Use test-driven development for code, keep storage and deployment boundaries explicit, and do not add secrets or uploaded runtime data to this public repository.
- Keep communication concise, source factual claims, and ask when requirements are unclear.
