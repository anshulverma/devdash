# devdash — Build Plan (M0–M5)

The milestone roadmap for building the library. Work milestones **in order**; each must be
runnable + tested before the next. Check boxes as acceptance criteria are genuinely met (verified by
running the command, not by assertion). Record progress in [`../PROGRESS.md`](../PROGRESS.md).

> Scope note: M0–M5 build the **library**. Adopting devdash into a specific host app (swapping its
> in-tree dashboard, migrating host data) is the host's work, tracked in that host's own repo — not
> here.

## M0 — Repo scaffold + CI + secret-scan gate
- [x] Apache-2.0 `LICENSE` committed
- [x] Monorepo: `packages/ui` (pnpm, Vite/React/TS, Tailwind preset stub), `packages/api`
      (Python, `pyproject.toml`, async SQLAlchemy + alembic skeleton), `docker/`, `examples/host-app`
- [x] `pnpm build` and `pip install -e packages/api` both succeed
- [x] CI (GitHub Actions): lint + typecheck + unit + build both packages, green
- [x] `gitleaks` (or equivalent) secret-scan gate runs on push

## M1 — Dashboard shell + tab-plugin API *(the named deliverable)*
- [ ] `TabDescriptor` type; mandatory `scrollModel` (D02); freeform `id`; `React.lazy`-able component
- [ ] `<DevDashboard>` build-time composition (D01); defaults not auto-injected
- [ ] Shell-owned `#<id>?<params>` routing + `useTabQuery<T>(codec)` (D03)
- [ ] `<DevDashboardProvider>` exposes ambient services; `--devdash-*` theme + Tailwind preset +
      neutral default; `branding` prop; `CategoryColorProvider`
- [ ] Primitives exported (stubs ok): `RecordTable`, `useEventSourceTail`, `FilterChips`,
      `TimeRangePicker`, `JsonDetailPanel`, `StatusStrip`
- [ ] Resilience: per-tab error boundary, duplicate-id throw (dev), unknown-hash fallback,
      zero-tabs empty state
- [ ] `examples/host-app` renders 2 placeholder tabs + 1 custom tab; deep-links work; theme override
      works; a thrown tab is isolated

## M2 — Backend mount model + engine lifecycle + own DB
- [ ] `make_dashboard_app(config)` + `mount_dashboard(host_app, config, path)` (D09)
- [ ] `dashboard_lifespan(config)`: engine built in-loop, DI to modules, disposed on shutdown (D10);
      pytest mounts the sub-app in a host app with **no cross-loop error**
- [ ] `DevDashConfig` (Pydantic settings, `DEVDASH_` env); auth (bearer + hook + open-with-warning);
      explicit CORS; metrics opt-in
- [ ] devdash owns its DB: `devdash db create` provisioning; expand-only + advisory-locked
      `devdash.migrate()`; documented owner/app role recipe
- [ ] `python -m devdash` standalone runner serves the shell + UI bundle; `GET
      {base_path}/__devdash/meta` handshake

## M3 — `LogSource` abstraction + adapters
- [ ] `LogSource` protocol (`search`/`tail`/`enumerate`/`capabilities`); `LogEntry` contract (open
      `fields`, optional `service`); stable entry id (D04); declared search semantics (D05);
      ingest-out-of-core (D06)
- [ ] In-memory adapter (default/test); `logsTab(config)` factory; capability-driven UI;
      SSE prime/entry/error + `Last-Event-ID` resume + drop-oldest `gap` marker
- [ ] Quickwit+Redis composite adapter (degrades to tail-only when search down)
- [ ] single-Postgres adapter (ILIKE/tsvector search, cursor-poll tail)
- [ ] In-memory adapter searches + tails in `examples/host-app`; capabilities disable search where
      absent

## M4 — Phases tracker (own DB)
- [ ] Tables migrated into devdash's owned DB; alembic baseline in devdash namespace
- [ ] Phase taxonomy + git-inference rules + price table as host config (keep word `phase`)
- [ ] Provider-neutral token ingest; bundled `[claude-code]` importer (D08); unknown-model → cost 0 + warn
- [ ] Projection optional (`method:"none"`); degraded manual-session mode; lib-provided `commit-msg` hook
- [ ] `phasesTab(config)` UI uses `CategoryColorProvider`; a host with a sample taxonomy tracks
      sessions + tokens + projection end-to-end in `examples/host-app`

## M5 — Release pipeline + example canary
- [ ] Lockstep version + `GET {base_path}/__devdash/meta` contract handshake (D12)
- [ ] OpenAPI emit → generated UI client + drift gate in CI
- [ ] Tag → npm provenance + PyPI Trusted Publishing + GHCR multi-arch; idempotent re-runnable publish
- [ ] `examples/host-app` exercises mount + custom tab + all log adapters; CI runs it against built packages
- [ ] `v0.1.0` publishes all three artifacts; a clean checkout consumes them

---

## Dependency order
M0 → M1 → M2 → (M3 ∥ M4) → M5.

## Definition of done (the completion promise)
Output the completion promise **only** when M0–M4 are fully checked AND `pnpm build`, `pytest`, and
lint all pass green, AND `examples/host-app` runs the Logs (in-memory) + Phases tabs end-to-end.
(M5 publishing is human-gated — do not publish to npm/PyPI/GHCR autonomously; leave the pipeline
configured but unfired.)
