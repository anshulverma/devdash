# devdash — Design

A pluggable operator/developer dashboard library. This document is the design source of truth.
Where a decision is referenced as **Dnn**, see [`ADRS.md`](ADRS.md).

## What devdash owns vs. what the host plugs in

| Concern | Owner |
|---|---|
| Dashboard shell (nav, routing, layout, theme injection, branding) | **devdash** |
| Tab-plugin API (`TabDescriptor`, registration, hash-query state, per-tab error boundary) | **devdash** |
| Viewer primitives (record-stream table, `useEventSourceTail`, filter chips, time-range picker, JSON detail panel, status strip) | **devdash** |
| **Logs** tab + `LogSource` abstraction + adapters | **devdash** |
| **Phases** tab (sessions, presence windows, token usage, projection, budgets, developers) + its **own Postgres DB** | **devdash** |
| Theme tokens / Tailwind preset / `CategoryColorProvider` / branding config | **devdash** |
| Backend mount API + standalone runner + config + auth hook + lifespan | **devdash** |
| Events tab, device registry, screenshots, any other tab | **host plugin** (built on devdash primitives) |
| Phase taxonomy content, git-inference rules, token price table, transcript importer, phase colors | **host config** |

## 1. Frontend tab-plugin API

```ts
interface TabDescriptor {
  id: string                       // freeform; becomes the hash route segment
  label: string
  component: ComponentType<TabProps> | LazyExoticComponent<ComponentType<TabProps>>
  scrollModel: 'scroll' | 'chrome' // MANDATORY, no default (D02)
  icon?: ReactNode
  defaultHash?: string
  order?: number
  enabled?: (ctx: DevDashContext) => boolean
  query?: QueryCodec<unknown>      // typed parse/serialize for deep-link filter state
}
```

- `<DevDashboard tabs={TabDescriptor[]} branding={...} theme={...} />` — build-time composition,
  not a runtime plugin loader (D01). Defaults are not auto-injected; the host assembles the array.
- Built-in tabs are exported factories: `logsTab(config)`, `phasesTab(config)`. They validate
  config synchronously at call time (fail at compose time, not operator runtime).
- `scrollModel` is required: `'chrome'` tabs (logs) own an internal scroller + pinned status strip
  (`overflow-hidden`); `'scroll'` tabs use the parent `overflow-auto`. No default — a wrong default
  silently clips live-arriving rows (D02).
- The shell owns `#<id>?<params>` routing + a typed `useTabQuery<T>(codec)` so every tab (built-in
  or custom) gets shareable deep links (D03). Filter state lives in the URL hash only.
- A `<DevDashboardProvider>` exposes ambient services (`apiBaseUrl`, pre-configured `fetch`,
  `useEventSourceTail`, `theme`, per-tab `query`, `branding`) to every tab.
- Resilience: per-tab `<Suspense>` + error boundary (one tab crashing must not blank the
  dashboard); a tab whose backend is absent shows a non-fatal banner; duplicate ids throw in dev;
  unknown hash falls back to the default tab; zero tabs → explicit empty state.
- Exported primitives (public, semver-governed): `RecordTable`, `useEventSourceTail`,
  `FilterChips`, `TimeRangePicker`, `JsonDetailPanel`, `StatusStrip`, `ThemeProvider`,
  `CategoryColorProvider`. These are the "shell" a host's custom tab reuses.

## 2. Logs — the `LogSource` abstraction

```python
class LogSource(Protocol):
    def search(self, filters: LogFilters) -> LogPage: ...
    async def tail(self, filters: LogFilters) -> AsyncIterator[LogEntry]: ...
    def enumerate(self) -> LogFacets:            # {services, levels} for filter chips
    def capabilities(self) -> LogCapabilities:   # static negotiation descriptor
```

- `capabilities()` = `{can_search, can_tail, can_enumerate, text_search: 'fulltext'|'substring'|'none', time_range, cursor_pagination}`.
  The UI reads it once on mount to hide/disable controls. A method an adapter lacks **fails loudly
  (501)** — never silent-empty.
- Log entry contract: required core `{ ts, service?, container, stream, level, message }` + an open
  `fields: dict[str,str]` for adapter-specific columns. `service` optional; `level` an open string
  with a known-value hint set.
- Entries carry an **adapter-supplied stable id** used for dedup / cursor / SSE-resume (D04). Search
  semantics are **declared per-adapter, never emulated** (D05). Ingest is **out of the core
  interface** — an optional per-adapter mixin (D06).
- SSE tail: `prime` (newest-N snapshot) / `entry` (one line) / `error` (terminal) + `: keepalive`
  comment (~30s). Reconnect via `Last-Event-ID`. Client ring ~5000 lines; drop-oldest + a `gap`
  marker on slow consumers.
- v1 adapters: (1) **Quickwit+Redis composite** (Quickwit search/enumerate + Redis-Streams tail;
  degrades to tail-only when search is unreachable); (2) **single-Postgres** (`logs` table; ILIKE/
  tsvector search; cursor-poll tail on `(ts,id)`); (3) **in-memory** (test/demo; default when
  unconfigured).

## 3. Phases — time/token/phase tracker (owns its own Postgres database)

- devdash **provisions and owns a dedicated Postgres database** (default `devdash`) for this tab —
  all tables, indexes, and its own alembic version table (D07). Provided a connection; production
  pre-provisions an empty DB + owner/app roles; migrations are expand-only + advisory-locked.
- Tables (ported into devdash's namespace): `sessions`, `presence_windows`, `token_usage`,
  `phase_config`, `phase_transitions`, `dev_settings`, `developers`, `projection_snapshots`,
  `push_resets`.
- Generic engine vs. host config: the **phase taxonomy** (keep the word `phase`; optional
  complexity/status/groups/colors), **git-inference rules** (path patterns, subject keywords,
  tag-prefix regex), the **token price table**, and the **transcript importer** are all host config
  / adapters. The engine treats phase keys as opaque.
- Provider-neutral token tracking: the ingest contract is the `POST tokens/import` row shape
  (`message_uuid`, ts, provider, model, token counts, optional cost, dev_name). A bundled-but-
  optional `[claude-code]` importer parses Claude Code `~/.claude` JSONL (D08). Unknown model →
  store with `cost=0` + warn (never guess rates).
- Projection (complexity-weighted burn-rate / finish-date) is optional — `method:"none"` when the
  taxonomy omits complexity. Degrades to manual-session mode with no taxonomy/git repo.
- UI uses `CategoryColorProvider` (host supplies a `phaseKey → color` resolver + fallback).

## 4. Backend integration

- `make_dashboard_app(config) -> FastAPI` sub-app factory (own CORS/middleware/metrics, isolated)
  + `mount_dashboard(host_app, config, path="/dev")` (D09). The same app object the standalone
  runner serves.
- `dashboard_lifespan(config)`: the async engine is built **inside the running loop** (never
  module-global), DI'd to modules, disposed on shutdown — loop-correct across mounted / standalone /
  pytest (D10). Mounted hosts MUST compose this lifespan into their own (Starlette does not run a
  mounted sub-app's lifespan).
- `DevDashConfig` (Pydantic settings, `DEVDASH_` env; precedence explicit arg > env > default):
  `database_url`, `enabled_tabs`, `log_source`, `phases`, `auth`, `base_path="/dev"`,
  `cors_origins` (never `*` default), `auto_migrate`, `enable_metrics`, `retention`,
  `branding`/`theme`.
- Auth: a default bearer-token mode guarding mutating routes + a host auth-dependency hook; neither
  set → open but loudly warned. CORS config-driven.
- Standalone runner: `python -m devdash` reads `DEVDASH_*`, runs migrations, serves
  `make_dashboard_app(config)` + the npm UI bundle from the wheel; a `devdash db create` subcommand
  provisions the database.
- `GET {base_path}/__devdash/meta` — unauthenticated contract-version handshake (D12).

## 5. Theming

- No host theme names baked in. Components reference `--devdash-*` CSS custom properties. devdash
  ships a neutral default theme + a Tailwind preset (`@devdash/ui/tailwind-preset`). Hosts override
  at runtime (CSS vars) or build time (preset). Branding (wordmark/logo/subtitle) is a prop.

## 6. Packaging & release

- Monorepo: `packages/ui` (pnpm), `packages/api` (Python), `docker/`, `examples/host-app`,
  `decisions/`. Apache-2.0 (D11).
- Lockstep single version across UI + backend + image (one git tag); contract-version handshake
  guards skew (D12). OpenAPI emitted from FastAPI → generated UI client + a CI drift gate.
- Tag → npm provenance + PyPI Trusted Publishing + GHCR multi-arch; idempotent re-runnable publish.
- `examples/host-app` exercises mount + a custom tab + all log adapters and is the CI canary.
