# devdash — Build Progress

The running log the ralph loop maintains across iterations. **Read this first each iteration** to
see what's done and what's next. Append a dated entry per iteration; keep the "Current state" block
at the top accurate.

## Current state
- **M0 + M1 + M2 COMPLETE ✅. M3: boxes 1,2,4,5 done** (only box 3 Quickwit+Redis left). **M4: box 1
  done** (phase tables + alembic baseline in devdash's owned DB).
- **Next concrete step (M4 box 2):** in `packages/api`, add the host phase **taxonomy** config (a
  YAML/dict of phases with label/status/complexity/display_order/parent/color — keep the word
  `phase`), seed `devdash_phase_config` from it on startup, and add the phases REST routes
  (GET phases, sessions CRUD). Git-inference rules + price table as host config. Then box 3 (token
  ingest + importer), box 4 (projection + manual mode + commit-msg hook), box 5 (phasesTab UI +
  example). Migrations now use alembic (run_sync, advisory-locked) — add a new revision per schema
  change, not create_all.
- **Known blockers:** none.

## Environment notes
- Node is **not** system-installed on this host; `scripts/bootstrap-node.sh` installs Node LTS
  (v24.16.0) + pnpm into `~/.local` (persistent). Always `export PATH="$HOME/.local/bin:$PATH"`.
- Python: use `uv` (no system pip). API venv: `packages/api/.venv`.
- pnpm 11 reads settings from `pnpm-workspace.yaml` (not the `pnpm` field in package.json).
  `onlyBuiltDependencies: [esbuild]` lives there. `.npmrc` sets `verify-deps-before-run=false`.
- TypeScript 6 requires `ignoreDeprecations: "6.0"` in tsconfig for tsup's dts build.

## Verification commands (run these; don't assume)
- UI: `cd /home/anshul/workspace/devdash && export PATH="$HOME/.local/bin:$PATH" && pnpm build && pnpm test && pnpm -C packages/ui typecheck`
- API: `cd /home/anshul/workspace/devdash/packages/api && . .venv/bin/activate && python -m pytest -q && python -m ruff check .`
- Example: `cd /home/anshul/workspace/devdash && pnpm -C examples/host-app build` (after M1 adds vite)

## Iteration log
### 2026-06-08 — iteration 7 — M4 box 1: phase tables + alembic baseline COMPLETE
- phases/models.py: 7 tables on devdash.metadata (sessions, token_usage, phase_config, phase_transitions, developers, dev_settings, projection_snapshots; BigInteger ids with sqlite Integer variant).
- Switched migrate() from create_all to ALEMBIC: programmatic Config + _alembic/ env.py (async run_sync pattern) + 0001_baseline. Postgres holds a session-level advisory lock on a separate connection spanning alembic's transaction; sqlite path is lock-free. Default alembic_version table (devdash owns the whole DB).
- **Verified:** full backend suite 36/36 on BOTH sqlite and real Postgres 17 (docker), incl. migrate-creates-7-tables + idempotent + advisory-locked PG path; ruff clean; wheel ships devdash/_alembic/{env.py,script.py.mako,versions/}.

### 2026-06-08 — iteration 6 — M3 box 4: SQL/Postgres LogSource adapter COMPLETE
- SqlLogSource: a `devdash_logs` table in devdash's OWNED database (self-managed via bind_engine, expand-only checkfirst; BigInteger id with sqlite Integer variant for rowid autoincrement). Portable substring search (case-insensitive LIKE), enumerate, cursor-poll tail on the autoincrement id (the stable id, D04) → real Last-Event-ID resume (cursor_pagination=True). ingest() mixin (not on the protocol, D06).
- Wired: dashboard lifespan binds the engine to bindable log sources after migrate; tail route reads the Last-Event-ID header into the resume cursor.
- **Verified:** 11/11 parametrized adapter tests pass on BOTH SQLite and real Postgres 17 (via docker); full backend pytest 27/27, ruff clean. Added a Postgres service to the CI api job (DEVDASH_TEST_PG_URL) so the PG path runs on every push.

### 2026-06-08 — iteration 5 — M3 boxes 2+5: logsTab UI + example COMPLETE
- @devdash/ui logs module: LogsClient transport abstraction; httpLogsClient (REST + SSE EventSource) and inMemoryLogsClient (client-side, fully working, push() drives the tail); capability-driven LogsTab (search box only when can_search, live toggle when can_tail, level chips from facets, bounded 5000 ring + dedup-by-id + drop-oldest gap marker in the status strip, declared search-mode label, JSON detail panel); logsTab(config) factory (scrollModel 'chrome').
- Backend SSE now emits per-event `id:` so EventSource auto-resumes via Last-Event-ID on reconnect (true server-side resume-from-cursor lands with the Postgres/Redis cursor adapters).
- examples/host-app: real Logs tab on the in-memory adapter, seeded + a 2s timer pushing synthetic live entries.
- **Verified:** vitest 22/22 (6 new logs tests incl. capability gating), backend pytest 21/21, ruff clean, UI build + example vite build green, leak scan clean.

### 2026-06-08 — iteration 4 — M3 box 1: LogSource backend abstraction COMPLETE
- logs subpackage: LogEntry contract (open fields, optional service, adapter-supplied stable id D04), LogFilters/LogPage/LogFacets, LogCapabilities (declared text_search D05). LogSource Protocol (search/tail/enumerate/capabilities); ingest is NOT on the protocol (D06).
- InMemoryLogSource (default adapter + test/demo): substring search, facets, live tail via subscriber queues, append() ingest mixin assigns stable ids + ring-trims.
- build_logs_router: GET /logs/{capabilities,facets,search} + SSE /logs/tail (prime/entry/error). Mounted into the dashboard when 'logs' tab enabled; log_source threaded through make_dashboard_app/mount_dashboard/dashboard_lifespan.
- **Verified:** pytest 21/21 (8 new logs tests incl. live-tail delivery + capability-driven 404 when tab disabled), ruff clean.

### 2026-06-08 — iteration 3 — M2 backend mount + engine lifecycle + own DB COMPLETE
- make_dashboard_app + mount_dashboard (sub-app factory, D09); dashboard_lifespan builds the async engine IN-LOOP (D10) and disposes on shutdown; engine never module-global.
- DevDashConfig (pydantic-settings, DEVDASH_ env); auth (open+warn / bearer / host hook); explicit CORS (never *); metrics opt-in. /__devdash/meta handshake (D12); honest 503 when lifespan unwired.
- Own DB (D07): devdash.metadata, expand-only advisory-locked migrate(), create_database() + `python -m devdash db create`; owner/app role recipe in docs/OPERATIONS.md.
- Standalone runner serves API + bundled UI (StaticFiles, placeholder until M5); verified the wheel ships devdash/static/.
- **Verified:** pytest 13/13 (incl. no-cross-loop mount regression test), ruff clean, wheel builds + includes static, `python -m devdash db create` works on sqlite.

### 2026-06-08 — iteration 2 — M1 dashboard shell + tab-plugin API COMPLETE
- @devdash/ui shell: TabDescriptor (mandatory scrollModel D02, freeform id, lazy-able), <DevDashboard> build-time composition (D01), shell-owned #<id>?<params> routing + useTabQuery (D03), DevDashboardProvider/useDevDash, CategoryColorProvider, neutral theme + themeToCssVars, per-tab TabErrorBoundary + Suspense, duplicate-id throw, unknown-hash fallback, zero-tabs empty state.
- Primitives exported: RecordTable, FilterChips, TimeRangePicker, JsonDetailPanel, StatusStrip, useEventSourceTail (ring + dedup-by-id + drop-oldest).
- examples/host-app: real DevDashboard with 2 placeholder tabs + 1 custom 'Records' tab built on primitives + deep-linked filter via useTabQuery + theme override + branding. Vite 8 build green.
- **Verified:** vitest 16/16, tsc --noEmit clean (ui + example), pnpm build green, example vite build green, leak scan clean. CI extended to build the example.

### 2026-06-08 — iteration 1 (cont.) — M0 COMPLETE, CI green
- Fixed CI: allowBuilds.esbuild (pnpm 11) + API uv venv. CI run 27125399349 all green (ui/api/secret-scan). All 5 M0 boxes ticked.

### 2026-06-08 — iteration 1 — M0 scaffold green
- Installed a persistent Node toolchain (`scripts/bootstrap-node.sh`): node v24.16.0, npm 11.13.0,
  pnpm 11.5.2.
- Monorepo scaffolded: `package.json` (pnpm workspace), `pnpm-workspace.yaml`, `tsconfig.base.json`,
  `.npmrc`, `.gitignore`.
- `packages/ui` (`@devdash/ui`): tsup build (ESM + d.ts), vitest, exports `DEVDASH_CONTRACT_VERSION`
  + a Tailwind preset stub mapping `devdash-*` → `--devdash-*`. **Verified:** `pnpm build` ✅,
  `tsc --noEmit` ✅, `vitest run` 2/2 ✅.
- `packages/api` (`devdash`): hatchling project, `src/devdash` with `__version__` +
  `CONTRACT_VERSION` + `__main__`, ruff + pytest config, `uv.lock`. **Verified:** `uv pip install -e
  '.[dev]'` ✅, `pytest` 2/2 ✅, `ruff check` ✅, `python -m devdash` runs ✅.
- `examples/host-app` (skeleton, imports `@devdash/ui`), `docker/Dockerfile` (skeleton),
  `.github/workflows/ci.yml` (ui + api + gitleaks secret-scan jobs), `.gitleaks.toml`,
  Apache-2.0 `LICENSE`.
- Leak scan clean: no `mantle`/`graymem`/host hostnames in source.
- **Not yet ticked:** "CI green" (awaits first GH Actions run); example-app build (needs M1 vite deps).
