# Nimbus Private Cloud

Nimbus is a private, multi-user file-storage application. The repository contains a FastAPI service, a plain HTML/CSS/JavaScript interface, SQL migrations, a local filesystem object adapter, and an S3-compatible adapter for MinIO.

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

## Public deployment: Netlify + Render + PostgreSQL + S3

The static frontend can be published on Netlify. The FastAPI server needs a separate public HTTPS host, a persistent PostgreSQL database, and S3-compatible object storage. The repository includes `netlify.toml` and `render.yaml`; these configure the static build and a **free Render API service only**. No paid resources or cloud accounts are created automatically.

1. Push this repository to a Git provider and import it into Netlify using the repository's `netlify.toml`.
2. In Netlify site environment variables, set `VITE_API_BASE_URL` to the Render API's HTTPS URL, for example `https://your-api.onrender.com`. Trigger a new deploy after setting it. The example is in `frontend\.env.production.example`.
3. In Render, create a Blueprint from the repository and apply `render.yaml`. Set the prompted `DATABASE_URL` to a persistent PostgreSQL connection string. A managed or external database may have usage limits or costs; check its retention and pricing before storing real data.
4. Create a private S3-compatible bucket and API key in an object-storage provider. Set `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, and `S3_SECRET_KEY` in the Render service environment. For Cloudflare R2, the endpoint format is `https://<account-id>.r2.cloudflarestorage.com`, and `S3_REGION` must be `auto`; create the `nimbus-private-files` bucket first. Do not put these storage credentials in Netlify or frontend variables.
5. After Netlify assigns the site's URL, set Render's `CORS_ORIGINS` to that exact origin (for example, `https://your-site.netlify.app`, with no trailing slash), then redeploy/restart the API.
6. Wait for Render's `/api/v1/health` health check. Open the Netlify URL and register a test account; test login, profile-photo upload, and file upload/download before sharing the site.

The frontend sends credentialed API requests to `VITE_API_BASE_URL`; production cookies use `Secure` and `SameSite=None` because Netlify and Render use different site domains. Browser policies can restrict cross-site cookies. For more reliable sessions, connect a custom domain and serve the UI and API from subdomains of the same registrable domain, then configure the Netlify URL in `CORS_ORIGINS`.

The free Render web service can sleep while idle, and the first request may be slow. This deployment configuration is a starting point, not a claim that the service is already published. Never use ephemeral local-disk storage for users' files in production; configure and verify the S3 bucket and persistent database first. Keep all secrets in provider environment settings, not in Git.

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
