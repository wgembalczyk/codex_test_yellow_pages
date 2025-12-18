# Project guidelines (must be followed in all future steps)

## Scope and delivery approach
- Implement only what is described in the current step. Do not add features from future steps.
- Keep the code as simple and readable as possible. Avoid enterprise patterns and over-engineering.
- Work iteratively: each step must be reviewable and testable.

## Technology constraints
- All components must be based on open-source libraries/tools.
- No database: runtime state is stored in RAM. Data loss after restart is acceptable.
- No cookies, no localStorage, no user sessions.
- External access is supported only via Cloudflare Tunnel (free). No router port-forwarding.

## Repo discipline
- Each step should be developed on a separate branch and merged via PR after tests pass.
- Prefer small, focused PRs per step/module.

## Architecture constraints
- Domain logic must remain framework-agnostic (no HTTP/Flask concerns in domain code).
- API layer should be thin and map domain errors to HTTP status codes cleanly.
- Frontend must be minimal (vanilla HTML/CSS/JS) and should not introduce unnecessary complexity.
