# devdash — Build Progress

The running log the ralph loop maintains across iterations. **Read this first each iteration** to
see what's done and what's next. Append a dated entry per iteration; keep the "Current state" block
at the top accurate.

## Current state
- **M0 + M1 + M2 COMPLETE ✅. M3 in progress** (box 1 done — LogSource backend). Box 2 (logsTab UI)
  next; then adapters (boxes 3,4); M4 may interleave.
- **Next concrete step (M3 box 2):** in `@devdash/ui`, add a `LogsClient` interface (search/tail/
  enumerate/capabilities), an `httpLogsClient(baseUrl)` (talks to the backend REST+SSE) and an
  `inMemoryLogsClient(entries)` (client-side demo), a capability-driven `LogsTab`, and a
  `logsTab(config)` factory (scrollModel 'chrome'). Wire it into examples/host-app (box 5).
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
