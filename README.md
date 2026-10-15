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

The root [`vercel.json`](./vercel.json) configures the Next.js frontend and
FastAPI backend as services in one Vercel project. Set the project root to the
repository root and connect `krishnarawatsf/OpenRelief-Engine`.

For Supabase's GitHub integration, this repository includes
[`supabase/config.toml`](./supabase/config.toml) and an initial migration under
`supabase/migrations/`. Set **Working directory** to `.` and **Production
branch name** to `master`. Enable **Deploy to production** to apply migrations
on pushes/merges to `master`. Automatic preview branches require the Supabase
Pro plan; that is optional for production schema deployment.
The initial migration enables PostGIS, creates the responder and incident
tables, and inserts the six campus responder units.

The public routes are `/api/*` and `/health` to the backend, and all other paths
to the frontend. The frontend calls `/api/*` on the same public origin, so there
is no server-to-server call and no internal service binding is needed. The
browser cannot consume a private runtime binding; the API rewrite is the
intentional public entry point.

Configure these production environment variables:

| Project | Variable | Value |
| --- | --- | --- |
| `openrelief-engine` | `DATABASE_URL` | Hosted PostgreSQL connection string with PostGIS enabled (required) |
| `openrelief-engine` | `AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME` | Azure OpenAI configuration (optional; mock triage otherwise) |
| `openrelief-engine` | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | Azure Speech configuration (optional; mock transcription otherwise) |
| `openrelief-engine` | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase project URL and anon key (optional; enables realtime) |

The schema portion of the initial migration mirrors
`backend/app/db/schema.sql`; the migration also seeds the six responders. For a
database managed by the Supabase GitHub integration, let that migration create
and seed the schema. Do not put database or Azure secrets in `NEXT_PUBLIC_*`
variables. Locally, set
`NEXT_PUBLIC_API_URL=http://localhost:8000` when running Next.js and FastAPI
separately; leave it unset on Vercel to use same-origin `/api/*` routing. Use
`vercel dev` from the repository root to run the configured services together.

## Checks

```sh
python3 -m unittest discover -s backend/tests -v
cd frontend && npm run typecheck && npm run lint
```
