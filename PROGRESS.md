# devdash — Build Progress

The running log the ralph loop maintains across iterations. **Read this first each iteration** to
see what's done and what's next. Append a dated entry per iteration; keep the "Current state" block
at the top accurate.

## Current state
- **Milestone in progress:** M0 (repo scaffold)
- **Next concrete step:** create the monorepo skeleton (`packages/ui`, `packages/api`, `docker/`,
  `examples/host-app`) + Apache-2.0 LICENSE; get `pnpm build` + `pip install -e packages/api` green.
- **Known blockers:** none

## Verification commands (run these; don't assume)
- UI: `cd /home/anshul/workspace/devdash/packages/ui && pnpm install && pnpm build && pnpm test`
- API: `cd /home/anshul/workspace/devdash/packages/api && pip install -e '.[dev]' && pytest && ruff check .`
- Example: `cd /home/anshul/workspace/devdash/examples/host-app && pnpm build`

## Iteration log
<!-- newest entries on top: ### <iso-date> — iteration N — <one line>; what changed; what's verified green; what's next -->
