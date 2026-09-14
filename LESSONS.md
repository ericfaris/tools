# Lessons

- **2026-09-14 — Design system pass ("Drafting Table").** A few gotchas
  worth remembering next time a design-system/ui-design pass touches this
  repo or another self-hosted app:
  - **Ideogram MCP has a shared, account-wide concurrent-generation limit.**
    `generate_image` calls fail with "Too many generations are running"
    whenever *other* sessions across the whole account (any project) have
    jobs in flight — `get_generation_status` with no `request_id` shows
    every session's queued/running jobs, not just this one. There's no way
    to reserve a slot; just retry the call periodically until one frees up.
    Don't burn a lot of turns retrying in a tight loop — space it out and do
    other prep work between attempts.
  - **Google Fonts' `css2` API silently returns a variable-font file if you
    request multiple weights in one query** (`family=X:wght@400;500;600;700`
    gave back the *same* file hash for every weight). Request each static
    weight in its own query (`family=X:wght@400`, separately for 500/600/700)
    to get distinct static woff2 files — check for this by comparing the
    returned URLs, not just trusting the weight label in the CSS comment.
  - **A translucent token used as a text/border color is an easy accessibility
    footgun.** This app's dark-mode `--panel` is intentionally ~50%-alpha (a
    "frosted vellum over the blueprint grid" effect), which is fine for
    backgrounds but would have made Run-button text semi-transparent if
    reused as a text color. Added a dedicated opaque `--on-accent` token
    instead of reusing a surface token for text-on-accent — worth grepping
    for any place a *surface* token is repurposed as a *text* color whenever
    a token comes back with alpha in it.
  - This repo's CSP has no external `font-src`/`style-src` allowance beyond
    `'self'` — any new design pass here must self-host fonts under
    `app/static/fonts/` rather than linking a Google Fonts CDN URL, which
    also happens to match the app's own "no third-party calls" privacy
    stance.
