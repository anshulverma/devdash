# devdash

A pluggable, open-source **operator/developer dashboard** you can mount into any project.

devdash ships two batteries-included tabs it fully owns — a **Logs** viewer (behind a pluggable
`LogSource` abstraction) and a **Phases** tracker (time + token + phase tracking, on its own
Postgres database) — plus a **generic tab-plugin API**, a **dashboard shell**, and reusable
**viewer primitives**. Everything else (your app's events tab, device registry, screenshots, …) is
a *host plugin* you build on top of devdash's shell. devdash never owns that data.

- **UI** — `@devdash/ui` (React + Vite + TypeScript + Tailwind), published to npm.
- **Backend** — `devdash` (FastAPI, mountable routers + standalone runner), published to PyPI.
- **Standalone** — a Docker image (GHCR) for running devdash as its own service.
- **License** — Apache-2.0.

> Status: pre-1.0, under active construction. See [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) for the
> milestone roadmap, [`docs/DESIGN.md`](docs/DESIGN.md) for the design, and
> [`docs/ADRS.md`](docs/ADRS.md) for the decisions.
