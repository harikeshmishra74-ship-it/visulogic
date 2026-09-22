# Vercel Deployment

## What To Deploy On Vercel

Deploy the `frontend` folder to Vercel.

Use these Vercel project settings:

- Framework Preset: `Vite`
- Root Directory: `frontend`
- Install Command: `npm install`
- Build Command: `npm run build`
- Output Directory: `dist`

Set this Vercel environment variable:

```text
VITE_API_BASE_URL=https://your-backend-host.example.com/api
```

The frontend includes `frontend/vercel.json` so direct links such as
`/mobile/scan/:token` load the React app instead of returning a 404.

## Backend Hosting

The current backend should not be deployed to Vercel as-is for the full app.
Vercel can run Python functions, but this backend uses SQLite, local uploads,
OpenCV processing, and generated files. Those need persistent storage and a
long-running API host.

Recommended MVP setup:

- Frontend: Vercel
- Backend: Render, Railway, Fly.io, a VPS, or another host with persistent disk
- Database/uploads: persistent disk for the MVP, then Postgres plus object storage

On the backend host, set:

```text
VISULOGIC_ENVIRONMENT=production
VISULOGIC_ALLOWED_ORIGINS=["https://your-vercel-app.vercel.app"]
VISULOGIC_DATABASE_URL=sqlite:////persistent/path/visulogic.db
VISULOGIC_UPLOAD_DIR=/persistent/path/uploads
```

After deployment, test:

1. Open the Vercel frontend URL.
2. Upload `data/demo-flowchart.png`.
3. Create a phone scan session.
4. Scan the QR code from a phone.
5. Confirm the mobile page opens on the Vercel domain and can upload to the backend.
