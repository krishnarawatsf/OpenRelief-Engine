# OpenRelief Engine

OpenRelief is an emergency-response demo for the SRM Institute of Science and
Technology campus in Kattankulathur. It combines AI-assisted triage, PostGIS
nearest-responder dispatch, a live map, and CAP v1.2 XML export.

## Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- Docker Compose and Docker (for the local PostGIS database)

## Configure and start

1. Copy `.env.example` to `.env` and fill in any Azure and Supabase credentials.
   Azure credentials are optional: triage uses a local mock without them.
2. Start the PostGIS database from the repository root:

   ```sh
   docker compose up -d db
   ```

   The container applies `backend/app/db/schema.sql` on its first start. If
   connecting to an existing database, apply that SQL file before seeding.
3. Install and seed the backend:

   ```sh
   python3 -m venv backend/.venv
   backend/.venv/bin/pip install -r backend/requirements.txt
   cd backend
   ../backend/.venv/bin/python -m app.db.seed
   ../backend/.venv/bin/uvicorn main:app --reload --port 8000
   ```
4. In a second terminal, configure the frontend environment and run it:

   ```sh
   cp .env.example frontend/.env.local
   cd frontend
   npm install
   npm run dev
   ```

   Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in
   `frontend/.env.local` to enable browser realtime. In Supabase, enable Realtime
   for the `public.incidents` table and ensure the anon role can read the rows
   that should appear on the dashboard. The backend separately uses `SUPABASE_URL`
   and `SUPABASE_ANON_KEY` if needed by future server-side integrations.

The dashboard is at <http://localhost:3000>, and the API is at
<http://localhost:8000>. The backend exposes `/health`, `/api/triage`,
`/api/responders`, `/api/incidents`, `PATCH /api/incidents/{id}/status`, and
`/api/incidents/{id}/cap.xml`. Resolving an incident returns its assigned
responder to the available pool.

## Current Vercel deployment

- Dashboard: <https://frontend-nine-dun-z1c05ngtla.vercel.app>
- API: <https://backend-phi-sand-90.vercel.app>

The dashboard and API are deployed and the API health check responds. Database
routes will return `503` until `DATABASE_URL` points to a reachable hosted
PostgreSQL database with PostGIS enabled and the schema and seed data have been
applied. Configure it in the `openrelief-api` Vercel project's Production
environment variables, then redeploy that project.

## Notes

- Local development defaults to `DATABASE_URL` from `.env.example`:
  `postgresql://openrelief:openrelief@localhost:5432/openrelief`.
- For audio triage, send a multipart request with a WAV file in the field named
  `audio` (uncompressed 16-bit PCM when Azure Speech is enabled). JSON requests
  use `{"text":"..."}`.
- Without Supabase credentials, the dashboard polls the API every five seconds.
  With Supabase credentials and Realtime enabled for `public.incidents`, new
  incidents are also delivered immediately.
- The safety override escalates transcripts containing `unconscious`, `bleeding`,
  `trapped`, `fire`, or `explosion` to urgency 5 / CAP severity Extreme.
- "Local offline mode" switches the frontend to a campus-local schematic map;
  it does not provide navigable cached OpenStreetMap tiles.

## Deploying to Vercel

The Next.js frontend and FastAPI backend are separate Vercel projects because
they use different runtimes:

- Frontend project: `openrelief-engine`, root directory `frontend`
- API project: `openrelief-api`, root directory `backend`

In the Vercel project settings, connect the GitHub repository
`krishnarawatsf/OpenRelief-Engine` to each project and set its root directory as
listed above. Configure these production environment variables:

| Project | Variable | Value |
| --- | --- | --- |
| `openrelief-engine` | `NEXT_PUBLIC_API_URL` | The deployed API origin, e.g. `https://backend-phi-sand-90.vercel.app` |
| `openrelief-engine` | `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (optional; enables realtime) |
| `openrelief-engine` | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key (optional; enables realtime) |
| `openrelief-api` | `DATABASE_URL` | Hosted PostgreSQL connection string with PostGIS enabled (required) |
| `openrelief-api` | `CORS_ORIGINS` | Comma-separated frontend origins, e.g. `https://frontend-nine-dun-z1c05ngtla.vercel.app` |
| `openrelief-api` | `AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME` | Azure OpenAI configuration (optional; mock triage otherwise) |
| `openrelief-api` | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | Azure Speech configuration (optional; mock transcription otherwise) |

Apply `backend/app/db/schema.sql` to the hosted database and run the responder
seed once with `DATABASE_URL` set before using database-backed routes. Do not
put database or Azure secrets in `NEXT_PUBLIC_*` variables. Vercel's project
root directory must be set to the relevant subfolder for Git-based deployments.
For CLI deployments, run `vercel --cwd backend --prod` and
`vercel --cwd frontend --prod`.

## Checks

```sh
python3 -m unittest discover -s backend/tests -v
cd frontend && npm run typecheck && npm run lint
```
