# Cockpit

A self-hosted personal (and optionally business) cockpit: **net worth** and personal income/spending, projects with a brief and dated journal, a 4-column task board,
finances (one-off + recurring, margins by period), clients, **North Star goals**, a **weekly check**,
**learning** (main/secondary paths with weekly, monthly, quarterly and semester milestones, plus a library of
books, articles, labs and writing), **trips**, global search (⌘/Ctrl+K) and a full JSON backup. Everything lives in your own Postgres. Inspired by
[CobraAl/business-cockpit](https://github.com/CobraAl/business-cockpit), rebuilt to run on a laptop
or a Raspberry Pi with no cloud accounts.

**Stack:** FastAPI + async SQLAlchemy + Alembic, PostgreSQL 16, React + TypeScript (Vite), nginx, Docker Compose.


## Install the app

Cockpit runs on your own computer. No account, no server: your data stays in one file on your machine.

**Mac (Apple Silicon: M1 or newer)** with [Homebrew](https://brew.sh):

```bash
brew tap devali00/cockpit https://github.com/DevAli00/cockpit
brew install --cask devali00/cockpit/cockpit
```

**Windows 10/11 (64-bit)** with [Scoop](https://scoop.sh):

```powershell
scoop bucket add cockpit https://github.com/DevAli00/cockpit
scoop install cockpit/cockpit
```

Then open **Cockpit** from Applications (Mac) or the Start menu (Windows).
Update later with `brew upgrade --cask cockpit` or `scoop update cockpit`.

**Without Homebrew or Scoop:** download the `.dmg` (Mac) or `-setup.exe` (Windows) from the
[latest release](https://github.com/DevAli00/cockpit/releases/latest). The app is not signed with a paid
certificate, so the first launch needs one confirmation:

- Mac: open it once, then *System Settings → Privacy & Security → Open Anyway*.
- Windows: on the blue SmartScreen window, *More info → Run anyway*.

Good to know:

- Each release lists the SHA-256 of every file in `SHA256SUMS.txt`. Homebrew and Scoop check it for you.
- The Homebrew cask clears macOS's quarantine flag after verifying that checksum, which is why the app opens
  without the confirmation above. If you would rather keep Gatekeeper's prompt, use the `.dmg` instead.
- Your data lives in `~/Library/Application Support/Cockpit` (Mac) or `%APPDATA%\Cockpit` (Windows), with a
  daily copy kept for 14 days. Uninstalling the app does not delete it.
- Intel Macs are not supported by the packaged app yet.

**Uninstall:** `brew uninstall --cask cockpit` (Mac), `scoop uninstall cockpit` (Windows), or *Settings → Apps →
Cockpit → Uninstall* if you used the Windows installer. Drag the app to the Bin if you used the `.dmg`.
Your data is left in place; delete the data folder above to remove it too.

## Personal first, business optional

Settings → *Show business tools* hides projects, clients and business finances entirely (nothing is deleted).
The home page ("Today") greets you and shows your #1 focus, North Star status, net worth and next trip.

- **Money → Net worth:** accounts you own (current, savings, investments, retirement, crypto, property, vehicle)
  and owe (loans, mortgage, credit cards). Record balances whenever you like, or once a month with
  *Update balances* (one date, every account, pre-filled). Net worth = assets − debts, using each account's
  latest balance on or before a date; history is drawn month by month, and accounts not updated in 45 days
  are flagged. Single currency (the one in Settings).
- **Money → Funds:** savings pots (travel, emergency, Hajj/Umrah, Eid & gifts, sadaqa & zakat, car, education,
  big purchase, wedding, home, other) with a target and optional deadline. Add or take out money; Cockpit shows
  what's left and what to set aside per month and per week, refuses withdrawals that would go below zero, and a
  travel fund can be linked to a trip (shown on the trip page). Funds label money already in your accounts, so
  they do not change net worth.
- **Money → Dashboard (everything connected):** a personal transaction can be *paid from* a fund (a flight from
  the travel fund) or go *into* one (Eid money into the gifts fund). Funds can fill themselves: a fixed amount every
  month on a chosen day, and/or a percentage of every personal income (all funds together: 100% max). The dashboard
  shows income, expenses, what went into funds, and what is *left over to spend*
  (income − expenses − into funds + expenses a fund paid for). Fund balances are computed from these links and
  rules rather than stored, so editing or deleting a transaction updates every fund at once. Changing a rule never
  rewrites the past: what the old rule produced before today is frozen into the fund's history.
- **Money → Income & spending:** personal transactions and recurring items (salary, rent, subscriptions)
  with personal categories, kept separate from business finances. Shows what you saved and your savings rate.

## Life cockpit modules

- **North Star:** goals with a target, current value and deadline. A marker shows the pace you "should" be at
  if you progressed evenly; you are *behind* when you trail it by more than 10 points (first week: *starting*).
- **Weekly check:** you define your own metrics (focus hours, sport, sleep…) with a target and an optional
  minimum-viable level. Each Sunday you log the week; Cockpit computes the week score (mean of value/target,
  each capped at 100%), whether it was a minimum-viable week, and flags a deload when energy is 2 or less.
  The "#1 focus next week" shows on the Overview.
- **Learning:** *Paths* (main or secondary) hold milestones on four horizons: weekly, monthly, quarterly, semester.
  The *Library* tracks books, articles, courses, labs, videos, papers and your own writing (idea, draft, published)
  with progress, ratings and notes. Progress moves an item along automatically (a started item is in progress,
  a finished one is done and dated).
- **Trips:** destination, dates, status (idea, planned, booked, done), budget, and a checklist of flights, stays,
  activities and to-dos with costs, compared with the budget.

## Desktop app (no Docker, no login)

A standalone version for one computer: double-click, and it runs. Same app, with the data in one SQLite
file in the user's application-data folder (`~/Library/Application Support/Cockpit` on macOS,
`%APPDATA%\Cockpit` on Windows). A copy of that file is kept every day for 14 days in `backups/` there.

```bash
./scripts/build-desktop.sh          # macOS: dist-desktop/Cockpit-<version>-mac-<arch>.dmg
.\scripts\build-desktop.ps1         # Windows x64 (needs Inno Setup): ...-windows-x64-setup.exe
```

`.github/workflows/desktop.yml` builds both on GitHub (Actions tab → *Desktop builds* → *Run workflow*).
PyInstaller cannot cross-compile, so each installer is built on its own OS.

**Publishing a release:** set the new `version` in `backend/pyproject.toml`, commit, then
`git tag v<version> && git push origin main v<version>`. The workflow builds the installers, creates the
GitHub release, rewrites `Casks/cockpit.rb` and `bucket/cockpit.json` with the new checksums
(`scripts/write-manifests.py`), and finally installs the release with Homebrew and Scoop on clean machines
and runs the app's self-test (`.github/workflows/verify-install.yml`).

- **Not signed.** macOS: first launch needs *System Settings → Privacy & Security → Open Anyway*
  (explained in the .dmg). Windows: SmartScreen → *More info → Run anyway*.
- **How it is put together:** `desktop/main.py` starts the API on `127.0.0.1` with a random port and shows it
  in a native web view (pywebview: WebKit on macOS, Edge WebView2 on Windows; falls back to the default browser
  if there is none). The window signs in with a random per-launch token; requests with another `Host` header
  are refused; the page gets no native API (the backup "save" dialog is opened by the server). Tables are
  created and upgraded at startup (`app/db/bootstrap.py`, additive changes only).
- **Moving data in:** `backend/.venv/bin/python scripts/import-into-desktop.py <backup.json>` (app closed), or
  *Settings & data → Backup → Restore* inside the app.
- **Verify a build:** `COCKPIT_DATA_DIR=/tmp/x COCKPIT_SELFTEST=/tmp/x/report.json <path to Cockpit binary>`
  opens the real window, signs in, creates a task, saves a backup, writes the report and quits.
- Local only: unlike the Docker version it is not reachable from a phone or another computer.

## Run it (laptop or Raspberry Pi)

Needs Docker with the Compose plugin. On a Pi use a **64-bit OS** (Raspberry Pi OS 64-bit); all images are multi-arch.

```bash
./scripts/init-env.sh          # asks for your login, writes .env with random secrets (mode 600)
docker compose up -d --build   # first build on a Pi takes a few minutes
```

Open `http://localhost:8080`, or from another device `http://<pi-hostname>.local:8080` / `http://<pi-ip>:8080`.
Change the port with `COCKPIT_PORT` in `.env`.

Only the web container publishes a port. Postgres and the API are reachable only inside the Compose network.

### Login

One owner account, taken from `COCKPIT_ADMIN_EMAIL` / `COCKPIT_ADMIN_PASSWORD` in `.env`.
**Forgot the password?** Edit `.env`, then `docker compose up -d`: the stored hash is reset on startup.
Login is rate-limited (5 attempts / 5 min per IP and per email).

### Backups

- In the app: **Data & profile → Backup** downloads / restores everything as JSON (restore is all-or-nothing).
- Database dump: `./scripts/backup.sh` writes `backups/cockpit-<timestamp>.sql.gz` and keeps the last 14.
  On a Pi, run it from cron and copy the files off the SD card:
  `0 3 * * * cd /home/pi/cockpit && ./scripts/backup.sh`

### Access beyond your LAN

The app speaks plain HTTP, which is fine on a trusted home network but not over the internet.
For remote access put it behind HTTPS (e.g. Tailscale `serve`, or Caddy/Cloudflare Tunnel) and set
`COCKPIT_COOKIE_SECURE=true`. Do not port-forward it as-is.

## Develop

```bash
# backend (Python 3.12), SQLite in tests so no Docker needed
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest                      # 175 tests
COCKPIT_TEST_DATABASE_URL=postgresql+asyncpg://... .venv/bin/pytest   # same suite on a throwaway Postgres

# frontend
cd frontend && npm install
npm test && npm run dev               # http://localhost:5173, proxies /api to :8000
```

Run the API against a local Postgres:

```bash
export COCKPIT_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cockpit
export COCKPIT_SECRET_KEY=$(openssl rand -hex 32) COCKPIT_ADMIN_EMAIL=you@example.com COCKPIT_ADMIN_PASSWORD=...
cd backend && .venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:create_app --factory --port 8000
```

Schema change: edit `app/db/models.py`, then `alembic revision --autogenerate -m "..."`
(review it; migrations must not import app code).

## Design decisions

- **Layers.** `domain/` (finance + task-ordering rules) and `services/` import neither FastAPI nor HTTP types; `api/` is a thin adapter that maps `NotFoundError`→404, `InvalidError`→422.
- **Single owner, no `user_id` columns.** This is a personal tool; multi-tenancy would add risk and code for no use. If you ever need teams, that is a schema change, not a patch.
- **Auth.** Argon2 password hash, JWT in an `HttpOnly; SameSite=Strict` cookie (scoped to `/api`), identical error for unknown user vs wrong password, constant-time-ish verify for unknown users. Cookie + same-origin nginx means no CORS and no token in JS.
- **Money** is `NUMERIC(12,2)` / `Decimal` end to end and travels as strings in JSON.
- **Recurring items** are stored once and expanded to transactions on read; nothing is generated for future billing days.
- **Task ordering** uses float positions so a move rewrites one row; when repeated moves exhaust precision the column is renumbered once.

## Known limits

- The login limiter is in-process memory: it resets on restart and assumes one backend worker (true here).
- Only login is rate-limited; other endpoints sit behind authentication on a private network.
- No CSRF token: `SameSite=Strict` cookies plus JSON-only bodies cover the realistic cases, but this is defence by browser behaviour.
- Search is `ILIKE` over a few tables: ample for personal data volumes, not a full-text engine.
- Frontend has unit tests for its pure helpers and API client only; pages were checked by hand against the running stack.

## Code signing policy

The Windows and macOS builds are **not code-signed yet**. Every release is built from this repository by
GitHub Actions ([workflow](.github/workflows/desktop.yml)) and published with SHA-256 checksums.

- Committers, reviewers and approvers: [DevAli00](https://github.com/DevAli00) (sole maintainer). Changes
  from anyone else arrive as pull requests and are reviewed before merging; every release is approved by the
  maintainer.
- Privacy: this program will not transfer any information to other networked systems unless specifically
  requested by the user or the person installing or operating it. It has no telemetry, no accounts and no
  update checks; your data stays in a file on your computer.

## License

MIT, see [LICENSE](LICENSE).
