# Tools — Vision & Product Spec

> A clean, private, self-hosted portal of everyday utility tools.
> No ads. No subscriptions. No dark patterns. Just tools that work, reachable anywhere on your network.

---

## 1. Vision

The web is full of free utility sites — "merge PDF," "convert image," "compress
file" — but most are hostile: plastered with ads, gated behind subscriptions,
or quietly harvesting the files and information you hand them. Many use
deceptive patterns to push paid plans or trick you into installing things.

**Tools** replaces that whole category with a single, calm portal you own. It
surfaces a grid of focused utilities you click into, each doing one job well.
You self-host it, so your files are processed on *your* machine and nobody is
monetizing your data or attention.

### The one-sentence pitch
> A self-hosted, ad-free portal that puts the everyday file/PDF/image tools you
> actually use in one clean place you control.

### Why it exists (problem)
- Public tool sites are cluttered, slow, and ad-ridden.
- They paywall basic functionality behind subscriptions.
- They upload your potentially-sensitive documents to unknown third parties.
- They use manipulative UX to phish for emails, payment info, or installs.

### What "good" looks like
- Open the portal → see all tools at a glance → click → do the task → done.
- Zero friction, zero noise, zero tracking.
- Trustworthy by construction: it's *your* server, *your* files.

---

## 2. Principles

1. **Delight is a feature, not decoration.** Every visit should spark a quiet
   "this is *cool* — glad I built this." Polish, motion, and craft are
   first-class requirements, not nice-to-haves (see §6.1).
2. **Clean over clever.** A quiet, uncluttered UI. Every pixel earns its place.
   Delight comes from craft and restraint, never from clutter.
3. **One tool, one job.** Each tool has a single clear purpose and an obvious flow.
4. **Privacy by ownership.** Self-hosted; files processed locally on the server you run.
5. **No dark patterns, ever.** No ads, upsells, fake urgency, or data harvesting.
6. **Frictionless.** Minimal clicks from "I have a file" to "I have my result."
7. **Extensible.** Adding a new tool is a small, well-defined unit of work — and
   new tools inherit the delight automatically via shared components/motion.

---

## 3. Target user & access model

- **Primary user:** Just the owner (you), with the option to share the URL with
  trusted people on the same network.
- **Access:** Self-hosted on your own network/server, reached from any device's
  browser. The container binds to `127.0.0.1` only; remote access ("anywhere")
  is provided by a **Cloudflare Tunnel** to a `tools.mooseflip.com` hostname —
  the same pattern used by slipcast and bookhunt.
- **Auth:** A single shared credential gates the entire portal, implemented as
  **HTTP Basic Auth** (`AUTH_USER` / `AUTH_PASS`), matching slipcast. No
  accounts, no user management — just one wall between the open internet and
  your tools. (The slipcast multi-user `AUTH_USERS=user:pass,...` fallback can
  be carried over verbatim if ever needed.)

---

## 4. How it works

- **Architecture:** Web portal (browser UI) backed by a server that does the
  heavy lifting.
- **Processing:** **Server-side.** Files are uploaded to your backend, processed
  with proven open-source tooling, and the result is returned for download.
  Because the backend is yours, this stays private.
- **Data handling:** Uploaded and generated files are treated as ephemeral —
  stored only as long as needed to complete the task, then auto-purged
  (see §8). No file is retained or logged beyond what's required to run the job.

---

## 5. Tools (v1 scope)

The first version ships four tool families. Each family is a set of focused
single-purpose tools surfaced as their own portal tiles.

### 5.1 PDF manipulation
- Merge multiple PDFs into one
- Split a PDF (by range, or into single pages)
- Reorder / rotate / delete pages
- Compress / reduce file size
- Add or remove a password / encryption

### 5.2 PDF conversions
- PDF ↔ Word/Office documents
- PDF → images (per page) and images → PDF
- PDF → plain text, including OCR for scanned PDFs

### 5.3 Image tools
- Convert between formats (PNG, JPG, WebP, etc.)
- Resize, crop, compress
- Background removal

### 5.4 File / format converters
- Document format conversion (Office ↔ PDF ↔ etc.)
- Audio / video format conversion
- Archive: zip / unzip

> **Note:** Tools beyond v1 (e.g. text utilities, QR codes, hashing, color
> tools) are explicitly out of scope for the first release but the architecture
> should make them cheap to add later.

---

## 6. User experience

- **Home / portal:** A clean grid of tool tiles, optionally grouped by family
  (PDF, Image, Convert). Each tile = icon + name + one-line description, with
  tactile hover/press states that make the grid feel alive.
- **Search/filter:** A quick filter to find a tool by name as the list grows.
- **Tool page:** Drag-and-drop or pick a file → choose options → run → download
  result. Clear, satisfying progress feedback for longer jobs.
- **Errors:** Plain-language messages ("This file isn't a valid PDF") — never
  raw stack traces. Even failure states should feel considered, not jarring.
- **Look & feel:** Minimal, modern, fast. Light/dark friendly. Mobile-usable.

### 6.1 The delight bar (the theme)

The defining theme of this app is **a fun, "wow" experience every single time** —
the kind that makes you think *"this is cool, I'm glad I wrote this."* This is a
core requirement, not polish bolted on at the end. Concretely:

- **Distinctive, not generic.** Avoid the default-AI/template look. The portal
  should have a memorable visual identity (consider the `ui-designer` skill).
- **Motion with meaning.** Smooth, purposeful micro-interactions — tile hovers,
  drag-and-drop feedback, page transitions, button presses. Tasteful, never
  gratuitous, and never at the expense of speed.
- **A great "drop a file" moment.** The upload interaction is the signature
  experience — it should feel responsive and a little magical.
- **Satisfying progress & completion.** Real-time progress and a rewarding
  "done!" moment (a flourish/confetti-grade beat on success — subtle, optional,
  tasteful).
- **Thoughtful details.** Empty states, loading skeletons, sounds-off-by-default
  niceties, keyboard shortcuts, copy that has personality without being cute.
- **Fast is part of the wow.** Snappiness *is* delight; animations must never
  make the app feel slow.

> Litmus test for any UI decision: *does this make the app more fun to use
> without making it slower or noisier?* If not, cut it.

---

## 7. Technical approach

Aligned with the established **slipcast / bookhunt** conventions. slipcast is the
direct template (Python/FastAPI self-hosted Docker app), so we mirror it.

- **Backend:** Python 3.12 + **FastAPI** served by **uvicorn** — best-in-class
  libraries and CLI tools for this domain (`pypdf`/`pikepdf` for PDF, `Pillow`
  for images, `ImageMagick`, `Ghostscript`, `ffmpeg`, `LibreOffice` headless for
  doc conversions, `Tesseract` for OCR, `rembg` for background removal).
- **App layout (mirrors slipcast):** an `app/` package — `main.py` (FastAPI app
  + auth/CSRF middleware), `config.py` (all env-driven config), per-domain
  modules, and static assets in `app/static/` (`styles.css`, `app.js`,
  `favicon.ico`, vendored libs under `app/static/vendor/`).
- **Frontend:** Server-rendered HTML + **vanilla JS** static assets — no build
  step, same as slipcast/bookhunt. The portal grid and tool pages are kept
  lightweight and snappy. (See §6/§12 for the delight bar this UI must clear.)
- **Auth:** **HTTP Basic Auth** middleware (`AUTH_USER`/`AUTH_PASS`), with the
  slipcast security hardening carried over: CSRF Origin/Referer check on
  state-changing requests, rate limiting on failed auth attempts, and a strict
  `Content-Security-Policy` header.
- **Config & data:** env-var driven via `config.py`. **No data volume** — the
  platform is stateless (see §8). All processing happens in memory.
- **Packaging & deploy:** **Docker** — `docker compose up`, image published as
  `ericfaris/tools:latest`, container bound to `127.0.0.1:<port>`,
  `restart: unless-stopped`, **`read_only` root filesystem + in-memory `/tmp`
  tmpfs, no volume**. The image bundles all the
  heavy system tools (ImageMagick, Ghostscript, ffmpeg, LibreOffice, Tesseract)
  so there's no host setup.
- **CI/release (mirrors slipcast):** GitHub Actions runs `pytest` on PRs and
  pushes to `main`; exact-pinned `requirements.txt` with **Renovate** opening
  bump PRs; a git **tag push** triggers the Docker Hub image build; a
  `.claude/commands/deploy.md` slash command tags → watches CI →
  `docker compose pull && up -d`.
- **Tool plugin pattern:** Each tool is a self-contained module declaring its
  metadata (name, family, icon, inputs/options) and a processing function. The
  portal builds its grid from the registry automatically, so adding a tool
  doesn't touch the core.

---

## 8. Non-functional requirements

- **Privacy/retention (zero-retention guarantee):** Uploads and intermediate
  artifacts live only in memory for one request and are discarded the instant
  the response is sent; uploads are explicitly closed even on failure. Nothing
  is persisted (read-only FS, in-memory `/tmp`, no volume), nothing is cached
  (`Cache-Control: no-store`), and nothing is logged (no access log, no activity
  logger). No analytics, no third-party calls, no telemetry. The owner cannot
  see what users do. Safe to share with friends and family. Enforced by
  `tests/test_privacy.py`.
- **Security (mirrors slipcast):** HTTP Basic Auth on all non-public routes;
  CSRF Origin/Referer check on state-changing requests; rate limiting on failed
  auth; strict `Content-Security-Policy`; container bound to `127.0.0.1`;
  validate/limit file types and sizes; sandbox/limit external tool invocation;
  sensible upload size caps; path-traversal prevention on any file paths.
- **Performance:** Snappy portal; animations stay 60fps and never block input;
  long-running conversions show progress and don't block the UI.
- **Delight:** Meets the §6.1 bar — the experience should feel polished and fun
  on every visit, on both desktop and mobile.
- **Reliability:** A failed tool job never takes down the portal.
- **Maintainability:** Clear separation between portal core and individual tools.

---

## 9. Non-goals (v1)

- Public/multi-tenant SaaS, billing, or user accounts.
- Real-time collaboration or file storage/library features.
- Mobile native apps (the web UI should be mobile-usable instead).
- Client-side/in-browser processing (revisit later for specific tools).
- Exhaustive tool coverage — depth and quality over breadth.

---

## 10. Success criteria

- **The wow holds.** Using it still sparks "this is cool, glad I built this"
  weeks in — not just on day one.
- You reach for *this* instead of a public tool site for everyday file tasks.
- A new tool can be added in a single focused change and inherits the polish.
- The portal stays clean and fast as tools accumulate.
- Files are demonstrably never retained or sent anywhere but your own server.

---

## 11. Project conventions (inherited from slipcast / bookhunt)

These are the house patterns this repo follows so it feels consistent with the
rest of the fleet:

- **Self-hosted Docker app**, image `ericfaris/tools:latest`, `docker-compose.yml`
  with `restart: unless-stopped`, `read_only` root + tmpfs `/tmp` (no volume),
  port bound to `127.0.0.1:<port>`.
- **Remote access** via **Cloudflare Tunnel** to `tools.mooseflip.com`
  (documented in a `CLOUDFLARE_TUNNEL.md`, as in slipcast).
- **HTTP Basic Auth** + security hardening (CSRF, rate limiting, CSP).
- **Config via env vars** centralized in `app/config.py`; `.env` + `.env.example`.
- **Exact-pinned `requirements.txt`** with **Renovate** (`renovate.json`).
- **GitHub Actions** `pytest` workflow on PR + push to `main`; `tests/` dir.
- **Tag-push → Docker Hub build**; `/deploy` slash command in
  `.claude/commands/deploy.md`.
- **README-driven** — a thorough top-level `README.md` (quick start, env vars,
  deploy).

---

## 12. Open questions / future

- Optional in-browser processing for small/sensitive files (no upload at all).
- Per-tool history or "recent results" (vs. strict ephemerality).
- Naming/branding for the portal (and how far to push the visual identity).
- Which additional tool families to add after v1.
- Should the multi-user `AUTH_USERS` fallback be enabled from the start?
