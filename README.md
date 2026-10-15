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
`/api/responders`, `/api/incidents`, and
`/api/incidents/{id}/cap.xml`.

## Notes

- Local development defaults to `DATABASE_URL` from `.env.example`:
  `postgresql://openrelief:openrelief@localhost:5432/openrelief`.
- For audio triage, send a multipart request with the file field named `audio`.
  JSON requests use `{"text":"..."}`.
- The safety override escalates transcripts containing `unconscious`, `bleeding`,
  `trapped`, `fire`, or `explosion` to urgency 5 / CAP severity Extreme.
- "Local offline mode" switches the frontend to a campus-local schematic map;
  it does not provide navigable cached OpenStreetMap tiles.

## Checks

```sh
cd frontend && npm run typecheck && npm run lint
```
