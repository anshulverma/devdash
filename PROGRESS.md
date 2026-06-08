# devdash — Build Progress

The running log the ralph loop maintains across iterations. **Read this first each iteration** to
see what's done and what's next. Append a dated entry per iteration; keep the "Current state" block
at the top accurate.

## Current state
- **M0–M4 ALL COMPLETE ✅** (27/27 feature boxes). Only M5 (release pipeline — human-gated publish)
  remains, which is OUT of the completion criterion. The example runs BOTH Logs (in-memory) + Phases
  tabs end-to-end.
- **Next (optional, M5 — human-gated):** lockstep version + contract handshake (already exists);
  OpenAPI client drift gate; npm/PyPI/GHCR publish workflow (configure, do NOT fire). M5 is outside
  the M0–M4 completion criterion.
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
### 2026-06-08 — iteration 12 — M3 box 3: Quickwit+Redis composite COMPLETE → M0–M4 DONE
- logs/quickwit_redis.py: QuickwitSearch (REST search + best-effort facets + /health/livez), RedisStreamTail (XADD ingest + XREAD tail; stream id = stable id, Last-Event-ID resume), QuickwitRedisLogSource composite (can_search∧can_tail, text_search 'fulltext'; refresh_health() degrades to tail-only when Quickwit unreachable). ingest mixin (D06). `[quickwit-redis]` extra (httpx+redis).
- **Verified:** 5 composite tests green incl. against REAL Redis 7 + Quickwit (docker: real index create+ingest+search, redis tail+resume); full backend 53/53; ruff clean. CI api job gains redis service + a Quickwit start step + the test env vars.
- **ALL M0–M4 boxes (27) checked.** Example runs Logs (in-memory) + Phases end-to-end.

### 2026-06-08 — iteration 11 — M4 box 5: phasesTab UI + example end-to-end COMPLETE (M4 DONE)
- @devdash/ui phases module: PhasesClient (httpPhasesClient over /phases REST + inMemoryPhasesClient for demo/tests); PhasesTab — projection card (finish-date when calibrated; 'add complexity' when method none), AI cost + messages cards, phase table with CategoryColorProvider color dots; phasesTab(config) factory (scrollModel 'scroll').
- examples/host-app now mounts BOTH phasesTab (sample taxonomy + colors via categoryColor) AND logsTab (in-memory) — runs Logs + Phases end-to-end.
- **Verified:** vitest 27/27 (5 new phases tests), backend pytest 48/48, ruff clean, UI build + example typecheck + vite build green, leak scan clean. ALL M4 boxes ticked.

### 2026-06-08 — iteration 10 — M4 box 4: projection + manual mode + commit-msg hook COMPLETE
- phases/projection.py: complexity-weighted compute_projection -> method none|naive|calibrated (none when no complexity; naive when nothing done; calibrated gives target/remaining/burn/finish-date). repository.projection_inputs + snapshot_projection; GET /phases/projection route.
- Degraded manual-session mode verified (no taxonomy -> sessions work, projection 'none').
- phases/hook.py: generic check_commit_message (tag via host tag_regex, membership in host phase keys), load_phase_keys (json/yaml), install_hook (.git/hooks/commit-msg); CLIs `devdash check-commit-msg` + `devdash install-hook`.
- **Verified:** backend pytest 48/48 (10 new: projection none/naive/calibrated + route + manual mode; hook extract/check/comments/key-loading/install), ruff clean.

### 2026-06-08 — iteration 9 — M4 box 3: token ingest + claude-code importer COMPLETE
- phases/tokens.py: TokenRow contract + ImportResult. repository.import_token_rows (idempotent on message_uuid; cost from host PriceTable; unknown model -> cost 0 + reported, D08) + token_stats (totals + by_model). routes: POST /phases/tokens/import, GET /phases/tokens/stats.
- importers/claude_code.py: pure-stdlib parser of ~/.claude JSONL transcripts -> TokenRow (parse_lines/parse_files/discover); `python -m devdash import-tokens --dev --url [--token] [--glob]` CLI POSTs via urllib. `[claude-code]` optional extra registered.
- **Verified:** backend pytest 38/38 (4 new: parser, cost-from-price-table, unknown-model->0+warn, idempotent), ruff clean, uv sync with new extra ok.

### 2026-06-08 — iteration 8 — M4 box 2: taxonomy host-config + phases routes COMPLETE
- phases/taxonomy.py: PhaseSpec / InferenceRules (tag_regex + path_patterns + subject_keywords) / PriceTable (cost() returns None for unknown models, D08) / PhaseTrackerConfig (from_dict). All host config; word 'phase' kept.
- phases/repository.py: seed_phases (insert-missing, non-destructive, idempotent), list_phases, sessions CRUD. phases/routes.py: GET /phases/phases (merges DB row + taxonomy color), GET/POST/PUT/DELETE /phases/sessions.
- Wired phases_config through Dashboard/make_dashboard_app/mount_dashboard/dashboard_lifespan; lifespan seeds phase_config after migrate; router mounted when 'phases' enabled.
- **Verified:** backend pytest 34/34 (8 new: taxonomy from_dict, price unknown->None, seed idempotent+non-destructive, GET phases color/order, full session CRUD incl. 404), ruff clean.

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
