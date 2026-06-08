# devdash — Architecture Decision Records

Each meets the bar: hard to reverse + surprising without context + a real trade-off.

- **D01 — Build-time descriptor composition, not a runtime plugin loader.** Hosts pass a static
  `TabDescriptor[]` to `<DevDashboard>`; ordering/removal/override are array operations.
- **D02 — `scrollModel` is mandatory, non-defaulted.** `'chrome'` tabs own an internal scroller +
  pinned status strip; a wrong default silently clips live-arriving rows.
- **D03 — Shell owns typed hash-query state for all tabs.** `#<id>?<params>` + a typed `QueryCodec`;
  filter state lives in the URL hash only.
- **D04 — Entry identity = adapter-supplied stable id, not a content hash.** Used for dedup / cursor
  / SSE-resume; content-hash is fallback only.
- **D05 — Search semantics declared per-adapter, never emulated.** `capabilities().text_search ∈
  {fulltext, substring, none}`; the UI labels the active mode; the lib never fakes richer search.
- **D06 — Ingest is out of the `LogSource` core interface.** Read+tail+enumerate+capabilities only;
  ingest is an optional per-adapter mixin so read-only adapters don't stub a write path.
- **D07 — devdash owns its own Postgres database (not a schema in the host's DB).** Provisions/
  migrates/owns the whole database incl. its own alembic version table; expand-only + advisory-
  locked migrations; production pre-provisions DB + owner/app roles.
- **D08 — Provider-neutral token ingest; transcript parsing is an adapter.** The engine contract is
  the `POST tokens/import` row shape; the Claude Code `~/.claude` parser is a bundled-but-optional
  `[claude-code]` adapter. Unknown model → cost 0 + warn.
- **D09 — Mount as a FastAPI sub-app factory, not `include_router`.** `make_dashboard_app(config)`
  owns its own CORS/middleware/metrics; `mount_dashboard` mounts it; same app object the standalone
  runner serves.
- **D10 — Engine + lifespan deferred to the running loop; never module-global.** Built inside
  `dashboard_lifespan`, disposed on shutdown, DI to modules → loop-correct across mounted/standalone/
  pytest. Mounted hosts must compose the lifespan (Starlette won't run a mounted sub-app's lifespan).
- **D11 — Apache-2.0 license.** Patent grant + permissive; devdash is embedded into closed host
  backends, so copyleft would force those hosts open.
- **D12 — Lockstep versioning of UI + backend + image; contract-version handshake.** One version per
  git tag; a contract-version integer at `GET {base_path}/__devdash/meta` (unauthenticated) guards
  skew.
- **D13 — Clean-history extraction + pre-publish secret-scan gate.** Fresh repo, no inherited
  history; a `gitleaks`/`trufflehog` gate guards every push; never commit host hostnames/DB-names/
  secrets to this public repo.
