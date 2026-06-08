# devdash — Build Progress

The running log the ralph loop maintains across iterations. **Read this first each iteration** to
see what's done and what's next. Append a dated entry per iteration; keep the "Current state" block
at the top accurate.

## Current state
- **M0 + M1 COMPLETE ✅.** Now starting **M2** (backend mount model + engine lifecycle + own DB).
- **Next concrete step:** in `packages/api`, implement `make_dashboard_app(config)` +
  `mount_dashboard()` (D09) and `dashboard_lifespan(config)` building the async engine in-loop (D10,
  fixes cross-loop flake). Add `DevDashConfig` (pydantic-settings, `DEVDASH_` env). Write a pytest
  that mounts the sub-app into a host FastAPI app with no cross-loop error. Then the own-DB
  provisioning (`devdash db create`) + expand-only advisory-locked `devdash.migrate()`.
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
