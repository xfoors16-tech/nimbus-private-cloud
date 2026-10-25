# Nimbus Private Cloud

Nimbus is a private, multi-user file-storage application. The repository contains a FastAPI service, a plain HTML/CSS/JavaScript interface, SQL migrations, a local filesystem object adapter, and an S3-compatible adapter for MinIO.

For step-by-step instructions in Arabic, see [RUN_AR.md](./RUN_AR.md).

## Current implementation

- Cookie-backed opaque sessions, Argon2id password hashes, CSRF checks on authenticated mutations, and role-guarded administrator user listing.
- User-scoped file/folder listings, uploads, downloads, rename, soft deletion, restore, permanent deletion, and folder creation.
- Per-user quota reporting and upload enforcement (2 GiB default); PostgreSQL serializes uploads by locking the owning user row.
- Random storage object keys, sanitized names, upload-size limits, isolated file operations, and a responsive vanilla JavaScript interface served by Vite.
- SQLite/filesystem are the no-services local defaults; Compose configures PostgreSQL and MinIO. Alembic migration is applied on API container startup.

Not yet complete: email verification and password reset, SMTP notifications, sharing, administrator account/quota controls and audit logs, recursive folder operations, move/preview APIs, file-signature scanning, persistent login rate limiting, malware scanning, a production reverse proxy/TLS deployment, and comprehensive integration/deployment testing. User verification, secure recovery, and rate limiting are especially important before any public deployment. MIME types supplied by clients are metadata only; files are always downloaded as attachments, and the application does not claim uploaded content is safe.

Trash files do not count against quota. A restore that would collide with a live filename returns a conflict. Permanent deletion removes the object and database record; backups are not built into the app.

## Local development (without Docker)

Requires Python 3.12+ and Node.js/npm.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Set-Location backend
python -m alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

In a second terminal:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

Open `http://localhost:5173`. The API docs are at `http://localhost:8001/docs`. The SQLite database and uploaded objects are stored under `backend\data` when the API runs from the backend directory. Vite proxies API requests to port 8001 by default; set `VITE_API_PROXY_TARGET` to override it.

To change configuration, set the corresponding environment variables before starting the backend. Important options include `DATABASE_URL`, `STORAGE_BACKEND` (`local` or `s3`), `STORAGE_ROOT`, `DEFAULT_QUOTA_BYTES`, `MAX_UPLOAD_BYTES`, `SESSION_COOKIE_SECURE`, and `CORS_ORIGINS`. Local mode is suitable for development only.

## Docker Compose

Install Docker Desktop, copy `.env.example` to `.env`, and replace all placeholder passwords with strong local-only values. Keep `DATABASE_URL`'s credentials consistent with `POSTGRES_USER` and `POSTGRES_PASSWORD`; likewise keep `S3_ACCESS_KEY`/`S3_SECRET_KEY` consistent with the MinIO root credentials. Then run from the repository root:

```powershell
docker compose -f docker-compose.yml up --build
```

The UI is at `http://localhost:5173`, API docs at `http://localhost:8000/docs`, MinIO console at `http://localhost:9001`, and Mailpit at `http://localhost:8025`. PostgreSQL and the MinIO API are only available on the internal Compose network. Named database and object-storage volumes persist across restarts. Do not remove volumes or run destructive resets without a verified backup.

Set both `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` in `.env` to provision the initial admin during API startup. Use a unique, long password; never use that mechanism as a production default. A normal user can register from the sign-in screen.

## No-card demo deployment: Netlify + PythonAnywhere

The repository is configured for Netlify static hosting and can run its FastAPI service on a PythonAnywhere free web app through the included WSGI adapter. This is a **small demonstration deployment**, not production cloud storage: PythonAnywhere's free account currently lists one web app, 512 MB disk space, and restricted outbound internet. The demo therefore uses SQLite and the account's local disk, with a 50 MiB quota per account and 5 MiB maximum upload. The total account disk is shared between code, installed packages, the database, and everyone’s uploaded files. Keep nonessential or sensitive files off the demo.

The Render blueprint is optional for people who later choose paid/external hosting. For the no-card path:

1. Import this repository into Netlify using `netlify.toml`. The API proxy target must match your PythonAnywhere username. In `netlify.toml`, replace `https://YOUR_USERNAME.pythonanywhere.com/api/:splat` with `https://<your-PythonAnywhere-username>.pythonanywhere.com/api/:splat`.
2. Create the PythonAnywhere **Beginner/free** account and note its username.
3. In a PythonAnywhere Bash console, clone the public repository and install the small WSGI-compatible dependency set:

   ```bash
   git clone https://github.com/xfoors16-tech/nimbus-private-cloud.git
   cd nimbus-private-cloud/backend
   mkvirtualenv --python=/usr/bin/python3.10 nimbus
   pip install -r requirements-pythonanywhere.txt
   mkdir -p ~/nimbus-data/objects
   export DATABASE_URL="sqlite:////home/$USER/nimbus-data/private-cloud.db"
   export STORAGE_BACKEND=local
   export STORAGE_ROOT="/home/$USER/nimbus-data/objects"
   python -m alembic upgrade head
   ```

   Choose a Python version actually offered in your PythonAnywhere Web tab and use its matching executable in the `mkvirtualenv` command if Python 3.10 is unavailable.
4. In PythonAnywhere **Web**, create a manual-config web app with the same Python version and set its virtualenv to `/home/<username>/.virtualenvs/nimbus`.
5. Open its WSGI configuration file. Add `/home/<username>/nimbus-private-cloud/backend` to `sys.path`, then import `application` from `pythonanywhere_wsgi`. Replace `<username>` in paths with your account username. Set `CORS_ORIGINS` to the exact Netlify site origin in this WSGI file; keep cookies secure, and retain the demo storage limits.
6. Reload the PythonAnywhere web app. Visit `https://<username>.pythonanywhere.com/api/v1/health`; it should return `{"status":"ok"}`.
7. Update Netlify's `/api/*` rewrite target in `netlify.toml` to that exact PythonAnywhere hostname, push the change to GitHub, and wait for Netlify to redeploy. Then test registration, login, profile photo, and small file upload/download from the Netlify site.

PythonAnywhere free accounts restrict some outbound internet connections; this deployment intentionally doesn't call S3 or another external storage service. Local persistent disk is limited, so the 50 MiB per-user quota is only an upper limit, not extra space promised to every registered account. Netlify's proxy has a 26-second timeout. Do not use this arrangement for sensitive personal data, important files, or production service guarantees. Keep the machine's local Netlify proxy setting and the production deploy target separate.

Never publish a secret or user data in GitHub. Don't configure cloud storage credentials on this free/local-disk deployment.

## Tests

```powershell
python -m pip install -r backend\requirements.txt
python -m pytest backend\tests -q
Set-Location frontend
npm.cmd ci
npm.cmd test
npm.cmd run build
```

Backend tests use an isolated in-memory SQLite database and an in-memory object-store stub; they do not touch a real account, database, or object bucket.

## Security and operations

- Cookies are `HttpOnly`, `SameSite=Lax`, and become `Secure` when `SESSION_COOKIE_SECURE=true`. Frontend write requests send the CSRF cookie value in `X-CSRF-Token`.
- Configure HTTPS, secure cookies, restrictive CORS origins, strong unique secrets, SMTP and account recovery, rate limiting, monitoring, backups, and dependency scanning before production.
- S3 credentials are server-side only. Object keys are not returned by API endpoints.
- The default development secrets in Compose must be replaced. Never commit `.env`.
- Database schema is managed by Alembic; back up both PostgreSQL and MinIO consistently.

## Demonstration checklist

1. Register two different accounts in separate browser profiles.
2. Upload a file and create a folder in the first account; check used quota.
3. Log into the second profile and verify its file list and search do not show the first account's content.
4. Attempt a download with the first profile's file ID from the second profile; the API returns `404`.
5. Trash and restore a file, then verify dashboard quota usage changes accordingly.
6. Open `/docs` to explore the versioned REST API.
