# devdash

A pluggable, open-source **operator/developer dashboard** you can mount into any project.

devdash ships two batteries-included tabs it fully owns — a **Logs** viewer (behind a pluggable
`LogSource` abstraction) and a **Phases** tracker (time + token + phase tracking, on its own
database) — plus a **generic tab-plugin API**, a **dashboard shell**, and reusable **viewer
primitives**. Everything else (your app's events tab, device registry, screenshots, …) is a *host
plugin* you build on top of devdash's shell. devdash never owns that data.

| Layer | Package | Stack |
|---|---|---|
| UI | `@devdash/ui` | React 18/19 + TypeScript + Tailwind (npm) |
| Backend | `devdash` | FastAPI + async SQLAlchemy (PyPI) |
| Standalone | `devdash` Docker image | the backend serving the bundled UI (GHCR) |

License: **Apache-2.0**. Design notes: [`docs/DESIGN.md`](docs/DESIGN.md) ·
decisions: [`docs/ADRS.md`](docs/ADRS.md).

> **Status: pre-1.0.** The packages are not published to npm/PyPI yet; consume via a git/path
> dependency for now.

---

## Contents

- [Concepts](#concepts)
- [Install](#install)
- [Quick start — standalone](#quick-start--standalone)
- [Mount into your own FastAPI app](#mount-into-your-own-fastapi-app)
- [Compose the dashboard UI](#compose-the-dashboard-ui)
- [Built-in tab: Logs](#built-in-tab-logs)
- [Built-in tab: Phases](#built-in-tab-phases)
- [Creating a custom tab](#creating-a-custom-tab)
- [Theming & branding](#theming--branding)
- [Viewer primitives](#viewer-primitives)
- [Configuration reference](#configuration-reference)
- [CLI reference](#cli-reference)

---

## Concepts

A devdash dashboard is a **build-time array of tabs** rendered by one shell:

```tsx
<DevDashboard tabs={[ logsTab(...), phasesTab(...), myEventsTab() ]} />
```

- A **tab** is a `TabDescriptor` — `{ id, label, component, scrollModel, … }`. There is no runtime
  plugin loader; you compose the array yourself, so ordering = array order and removing a tab = not
  including it.
- The two **built-in tabs** (`logsTab`, `phasesTab`) are factories that take a *client* and return a
  `TabDescriptor`. The client abstracts transport, so the same tab works against the HTTP backend or
  a client-side in-memory store (great for demos/tests).
- A **custom tab** is just a `TabDescriptor` whose `component` is your own React component. Reuse the
  exported **viewer primitives** (`RecordTable`, `FilterChips`, `StatusStrip`, …) so it matches the
  built-ins.
- The **backend** is a FastAPI sub-app you either run standalone or mount into your app. It **owns
  its own database** for the Phases tab and exposes the Logs + Phases REST/SSE routes.

---

## Install

```bash
# UI (git dependency until published)
pnpm add github:anshulverma/devdash#main --filter ./packages/ui   # or a path/workspace dep
# Backend
pip install "devdash @ git+https://github.com/anshulverma/devdash#subdirectory=packages/api"
# optional adapters/importers:
pip install "devdash[quickwit-redis]"   # httpx + redis, for the Quickwit+Redis log adapter
```

`@devdash/ui` declares `react` / `react-dom` as peer dependencies (>=18).

---

## Quick start — standalone

The fastest way to see it: run the backend as its own service against a zero-config SQLite database.

```bash
export DEVDASH_DATABASE_URL="sqlite+aiosqlite:///./devdash.db"
python -m devdash db create     # provision + migrate the devdash-owned database
python -m devdash serve         # serves the API + bundled UI at http://127.0.0.1:8000/dev
```

Open `http://127.0.0.1:8000/dev`. In production, point `DEVDASH_DATABASE_URL` at a **dedicated
Postgres database devdash owns** (see [Operations](docs/OPERATIONS.md) for the owner/app role
recipe).

---

## Mount into your own FastAPI app

devdash mounts as a **sub-application**. Because Starlette does not run a mounted sub-app's
lifespan, `mount_dashboard` returns a lifespan you **must compose** into your app's lifespan — this
is what builds the async engine (on the running loop) and runs migrations.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from devdash import DevDashConfig, mount_dashboard

config = DevDashConfig(
    database_url="postgresql+asyncpg://devdash_app:...@db/devdash",
    base_path="/dev",
    auto_migrate=False,   # let your release pipeline run `devdash.migrate` as the owner role
)

# `mount_dashboard` mounts the sub-app and returns the lifespan you must compose.
# A small holder lets the lifespan (defined before the mount) reach it:
_dash = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with _dash["lifespan"]():   # builds the engine on the running loop + migrates
        yield

app = FastAPI(lifespan=lifespan)
_dash["lifespan"] = mount_dashboard(app, config, path="/dev")
```

> Forgetting to compose the lifespan is the one easy mistake — the routes then return an honest
> `503` ("devdash not started") instead of silently using an uninitialised engine.

If you want devdash as its **own** app object (e.g. behind your own ASGI router), use
`make_dashboard_app(config)` — it wires the lifespan for you and is exactly what the standalone
runner serves.

> **devdash owns its database.** Point `database_url` at a database devdash owns end to end (its own
> tables + its own `alembic_version`). Migrations are expand-only and advisory-locked, safe under
> blue/green rollout.

---

## Compose the dashboard UI

```tsx
import { createRoot } from 'react-dom/client'
import {
  DevDashboard,
  logsTab, httpLogsClient,
  phasesTab, httpPhasesClient,
} from '@devdash/ui'

const base = '/dev'   // wherever you mounted the backend

createRoot(document.getElementById('root')!).render(
  <DevDashboard
    tabs={[
      logsTab({ client: httpLogsClient({ baseUrl: base }) }),
      phasesTab({ client: httpPhasesClient({ baseUrl: base }) }),
    ]}
    branding={{ wordmark: 'Acme / Dev' }}
    theme={{ 'color-primary': '#3b6ea5' }}
    categoryColor={(key) => ({ ui: '#3b6ea5', api: '#2e7d4f' })[key]}
  />,
)
```

`<DevDashboard>` props:

| prop | type | notes |
|---|---|---|
| `tabs` | `TabDescriptor[]` | required; the complete tab set, in display order |
| `branding` | `{ wordmark, logo?, subtitle? }` | nav identity |
| `theme` | `Record<string,string>` | overrides `--devdash-*` CSS vars |
| `apiBaseUrl` | `string` | exposed to tabs via `useDevDash()` |
| `fetch` | `typeof fetch` | pre-configured fetch (auth header, etc.) for tabs |
| `categoryColor` | `(key) => string \| undefined` | resolver behind `CategoryColorProvider` |

The shell owns hash routing (`#<id>?<params>`), per-tab error boundaries, lazy-loading, a zero-tabs
empty state, and unknown-hash fallback.

---

## Built-in tab: Logs

The Logs tab is **capability-driven**: it renders search only if the source can search, a live-tail
toggle only if it can tail, etc. Pick a **`LogSource`** adapter on the backend.

### Backend — choose an adapter

```python
from devdash import (
    DevDashConfig, make_dashboard_app,
    InMemoryLogSource, SqlLogSource, QuickwitRedisLogSource,
)

# (a) in-memory — zero infra; the default when none is given. Great for demos/dev.
app = make_dashboard_app(config, log_source=InMemoryLogSource())

# (b) single-Postgres/SQLite — a `devdash_logs` table in devdash's own DB.
#     Substring search + cursor-poll tail with real Last-Event-ID resume.
app = make_dashboard_app(config, log_source=SqlLogSource())

# (c) Quickwit (search) + Redis Streams (tail) — full-text search; degrades to
#     tail-only when Quickwit is unreachable. Needs `devdash[quickwit-redis]`.
app = make_dashboard_app(config, log_source=QuickwitRedisLogSource(
    quickwit_url="http://quickwit:7280", index="logs",
    redis_url="redis://redis:6379", stream="devdash:logs",
))
```

Adapters expose the same routes under `{base_path}/logs`: `…/capabilities`, `…/facets`,
`…/search`, and an SSE `…/tail`. The `SqlLogSource` and `QuickwitRedisLogSource` also have an
`ingest(entries)` mixin (ingest is intentionally *not* on the `LogSource` interface).

### Frontend

```tsx
import { logsTab, httpLogsClient } from '@devdash/ui'

logsTab({ client: httpLogsClient({ baseUrl: '/dev' }) })
```

For a backend-free demo or a unit test, use the in-memory client (it fully works client-side; `push`
drives the live tail):

```tsx
import { logsTab, inMemoryLogsClient } from '@devdash/ui'

const client = inMemoryLogsClient([
  { id: '1', ts: new Date().toISOString(), level: 'info', message: 'started', service: 'api' },
])
setInterval(() => client.push({ id: crypto.randomUUID(), ts: new Date().toISOString(), level: 'warn', message: 'tick', service: 'api' }), 2000)

logsTab({ client, label: 'Logs' })
```

A **log entry** is `{ id, ts, level, message, service?, container?, stream?, fields? }` — `id` is an
adapter-supplied stable id (used for dedup + tail resume); `fields` is an open map for
adapter-specific columns.

---

## Built-in tab: Phases

Tracks work **phases**, **sessions**, and **token usage**, with a complexity-weighted **projection**.
The word "phase" is devdash's; the *content* (your phases, git-inference rules, token price table) is
**host config**.

### Backend — supply a taxonomy

```python
from devdash import (
    DevDashConfig, make_dashboard_app,
    PhaseTrackerConfig, PhaseSpec, PriceTable,
)
from devdash.phases.taxonomy import ModelRate

tracker = PhaseTrackerConfig(
    phases=[
        PhaseSpec(key="ui",    label="UI",    status="in_progress", complexity=5, color="#3b6ea5"),
        PhaseSpec(key="api",   label="API",   status="done",        complexity=3, color="#2e7d4f"),
        PhaseSpec(key="infra", label="Infra", status="pending",     complexity=4, color="#b8860b"),
    ],
    prices=PriceTable(rates={
        # USD per 1M tokens
        "your-model": ModelRate(input=3.0, output=15.0, cache_read=0.3, cache_creation=3.75),
    }),
)

app = make_dashboard_app(config, phases_config=tracker)
```

devdash seeds `phase_config` from the taxonomy on startup (your dashboard edits win on re-seed) and
exposes routes under `{base_path}/phases`:

| route | purpose |
|---|---|
| `GET /phases/phases` | the phase table (merged with taxonomy color) |
| `GET/POST/PUT/DELETE /phases/sessions` | manual sessions CRUD |
| `POST /phases/tokens/import` | provider-neutral token ingest (idempotent on `message_uuid`) |
| `GET /phases/tokens/stats` | totals + by-model cost |
| `GET /phases/projection` | `method ∈ none\|naive\|calibrated` + finish-date/burn |

**Token ingest is provider-neutral.** Each row is
`{ message_uuid, ts, model, dev_name, provider?, input_tokens?, …, cost_usd? }`. If `cost_usd` is
omitted, devdash computes it from your `PriceTable`; an **unknown model yields cost 0 and is
reported** (never a guessed rate).

**Importing Claude Code usage** (an optional bundled adapter):

```bash
python -m devdash import-tokens --dev ada --url https://host/dev \
  --token "$DEVDASH_AUTH_TOKEN"            # parses ~/.claude/**/*.jsonl and POSTs the rows
```

**Projection** degrades gracefully: no complexity on your phases → `method:"none"` (the UI hides the
finish-date card); complexity but nothing done → `naive`; otherwise `calibrated` with a projected
finish date. With no taxonomy at all, the tab still works in manual-session mode.

### Frontend

```tsx
import { phasesTab, httpPhasesClient } from '@devdash/ui'

phasesTab({ client: httpPhasesClient({ baseUrl: '/dev' }) })
```

Or, client-side for demos/tests:

```tsx
import { phasesTab, inMemoryPhasesClient } from '@devdash/ui'

phasesTab({ client: inMemoryPhasesClient({
  phases: [{ phase: 'ui', label: 'UI', status: 'in_progress', complexity: 5 }],
  tokenStats: { messages: 128, input_tokens: 90000, output_tokens: 12000, cost_usd: 4.2, by_model: {} },
  projection: { method: 'calibrated', cumulative_sec: 36000, remaining_sec: 72000, target_sec: 108000, burn_per_day_sec: 7200, projected_finish_date: '2026-07-15' },
}) })
```

### Lib-provided commit-msg hook (optional)

devdash ships a generic commit-msg validator that checks a commit's phase tag (`[ui] …` or `ui: …`)
against *your* phase keys:

```bash
# keys come from a JSON/YAML file you control (a list of keys or a {phases:[{key}]} doc)
python -m devdash install-hook --repo . --phases-file ./phases.json
# the installed .git/hooks/commit-msg calls:  devdash check-commit-msg "$1" --phases-file ./phases.json
```

---

## Creating a custom tab

devdash owns Logs + Phases; **everything else is yours.** A custom tab is a `TabDescriptor` whose
`component` is your React component, reusing devdash's primitives + hooks. This is the
"events tab" pattern: *devdash provides the shell, you own the data.*

### 1. Your backend route (on your app)

```python
# your_app/events.py — your data, your endpoint, mounted on YOUR FastAPI app
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/events")
async def list_events() -> list[dict]:
    return [
        {"id": "1", "ts": "2026-06-08T00:00:01Z", "type": "calendar.synced", "severity": "info"},
        {"id": "2", "ts": "2026-06-08T00:00:02Z", "type": "oauth.failed",    "severity": "error"},
    ]

# app.include_router(router)  +  mount_dashboard(app, config)
```

### 2. Your tab component (reusing devdash primitives + hooks)

```tsx
import { useEffect, useState } from 'react'
import {
  RecordTable, FilterChips, StatusStrip, JsonDetailPanel,
  useDevDash, useTabQuery,
  type TabDescriptor, type TabProps, type QueryCodec,
} from '@devdash/ui'

interface Event { id: string; ts: string; type: string; severity: string }

// deep-linkable filter state: #events?sev=error
const codec: QueryCodec<{ sev: string[] }> = {
  parse: (p) => ({ sev: p.get('sev') ? p.get('sev')!.split(',') : [] }),
  serialize: ({ sev }) => new URLSearchParams(sev.length ? { sev: sev.join(',') } : {}),
}

function EventsTab(_props: TabProps) {
  const { fetch, apiBaseUrl } = useDevDash()        // ambient services
  const [filter, setFilter] = useTabQuery(codec)    // shell-owned hash state
  const [rows, setRows] = useState<Event[]>([])
  const [selected, setSelected] = useState<Event | null>(null)

  useEffect(() => {
    fetch('/api/events').then((r) => r.json()).then(setRows)
  }, [fetch])

  const shown = filter.sev.length ? rows.filter((e) => filter.sev.includes(e.severity)) : rows

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '0.75rem 1rem' }}>
        <FilterChips
          options={[{ value: 'info' }, { value: 'warn' }, { value: 'error' }]}
          selected={filter.sev}
          onChange={(sev) => setFilter({ sev })}
        />
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '0 1rem' }}>
        <RecordTable
          rows={shown}
          rowKey={(e) => e.id}
          columns={[
            { key: 'ts', header: 'time', width: 200 },
            { key: 'severity', header: 'severity', width: 90 },
            { key: 'type', header: 'type', render: (e) => (
              <button onClick={() => setSelected(e)} style={{ all: 'unset', cursor: 'pointer' }}>{e.type}</button>
            ) },
          ]}
        />
        {selected && <JsonDetailPanel value={selected} />}
      </div>
      <StatusStrip live={false}>{shown.length} events</StatusStrip>
    </div>
  )
}

// 3. register it (a plain TabDescriptor)
export const eventsTab: TabDescriptor = {
  id: 'events',
  label: 'Events',
  scrollModel: 'chrome',   // 'chrome' = the tab owns its own scroller + pinned strip
  component: EventsTab,     // may also be a React.lazy(...) for code-splitting
}
```

```tsx
<DevDashboard tabs={[ logsTab({ client }), phasesTab({ client }), eventsTab ]} />
```

**`scrollModel` is required, no default.** Use `'scroll'` for long-form tabs (the shell scrolls);
use `'chrome'` for tabs with their own internal scroller + a pinned footer/status strip (logs,
events). Picking the wrong one is the one thing that silently clips live-arriving rows.

For a live-tailing custom tab, use the `useEventSourceTail` hook (bounded ring + dedup-by-id +
drop-oldest) instead of a one-shot fetch.

---

## Theming & branding

devdash is theme-neutral — components read `--devdash-*` CSS custom properties, and a bundled
neutral theme makes it look finished out of the box. Override at **runtime** (the `theme` prop) or
**build time** (the Tailwind preset):

```tsx
<DevDashboard
  theme={{ 'color-primary': '#4A6670', 'color-surface': '#FFFCF7', 'radius-md': '10px' }}
  branding={{ wordmark: 'Acme / Dev', subtitle: 'internal' }}
/>
```

```ts
// tailwind.config.ts — extend the preset so your tab markup can use devdash-* utilities
import preset from '@devdash/ui/tailwind-preset'
export default { presets: [preset], /* … */ }
```

Phase/category colors come from a host resolver behind `CategoryColorProvider` (the `categoryColor`
prop). Inside a custom tab, `useCategoryColor()` returns `(key) => color` with a deterministic
fallback palette.

---

## Viewer primitives

Exported from `@devdash/ui` for custom tabs to match the built-ins:

| primitive | what |
|---|---|
| `RecordTable` | columnar, time-ordered record table |
| `FilterChips` | multi-select chip filter |
| `TimeRangePicker` | relative time-range selector |
| `JsonDetailPanel` | pretty-printed JSON detail |
| `StatusStrip` | pinned status strip (live dot + counts) |
| `useEventSourceTail` | SSE tail hook (prime/entry/error, bounded ring, dedup, drop-oldest) |
| `useDevDash` | ambient services: `{ apiBaseUrl, fetch, branding, theme }` |
| `useTabQuery` | typed, deep-linkable hash filter state for the active tab |
| `useCategoryColor` | `(key) => color` with fallback palette |

---

## Configuration reference

`DevDashConfig` (pydantic-settings; reads `DEVDASH_*` env vars; explicit args win):

| field / env | default | meaning |
|---|---|---|
| `database_url` / `DEVDASH_DATABASE_URL` | `sqlite+aiosqlite:///./devdash.db` | the devdash-**owned** database |
| `base_path` / `DEVDASH_BASE_PATH` | `/dev` | mount path of the dashboard sub-app |
| `cors_origins` / `DEVDASH_CORS_ORIGINS` | `[]` | explicit allow-list (never `*`) |
| `auth_token` / `DEVDASH_AUTH_TOKEN` | `None` | bearer token guarding mutating routes |
| `enable_metrics` / `DEVDASH_ENABLE_METRICS` | `False` | expose Prometheus `/metrics` |
| `auto_migrate` / `DEVDASH_AUTO_MIGRATE` | `True` | run migrations in the lifespan |
| `enabled_tabs` / `DEVDASH_ENABLED_TABS` | `{logs, phases}` | which built-in backends to mount |

**Auth:** set `auth_token` for a bearer default, or pass `auth_hook=<FastAPI dependency>` to
`make_dashboard_app`/`mount_dashboard` to own access entirely. With neither set, the dashboard is
open and logs a loud warning. The `GET {base_path}/__devdash/meta` handshake endpoint is always
unauthenticated (the UI reads it before it has credentials).

---

## CLI reference

```
python -m devdash serve [--host H] [--port P]      # serve API + bundled UI
python -m devdash db create                        # provision + migrate the owned database
python -m devdash import-tokens --dev NAME --url URL [--token T] [--glob PATTERN]
python -m devdash check-commit-msg <msgfile> --phases-file <file>
python -m devdash install-hook [--repo .] --phases-file <file>
```

---

See [`examples/host-app`](examples/host-app) for a runnable composition that mounts the Logs
(in-memory) and Phases tabs plus a custom tab.
