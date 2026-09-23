# Vercel Deployment Guide

VisuLogic supports two deployment architectures on Vercel:

---

## Option 1: Unified All-in-One Deployment (Frontend + Backend on Vercel)

Both the React + Vite frontend and the FastAPI backend run together within a single Vercel project using Vercel Serverless Functions (`@vercel/python`).

### Repository Structure for Vercel
- `vercel.json` (root): Routes `/api/*` to `api/index.py` and all other paths to `frontend/dist` (with SPA fallback).
- `api/index.py`: Serverless entrypoint exposing the FastAPI `app` with serverless-safe defaults.
- `requirements.txt` (root): Installs Python dependencies with `opencv-python-headless` (to avoid missing X11/OpenGL libraries on AWS Lambda).
- `frontend/`: React + Vite single-page application.
- `backend/`: Core FastAPI business logic, image processing, and database layer.

### Vercel Project Settings (Dashboard)
When creating or configuring your project in the Vercel Dashboard:

- **Framework Preset**: `Other` (or auto-detected from `vercel.json`)
- **Root Directory**: `.` (leave as repository root, **do not** select `frontend`)
- **Build Command**: `cd frontend && npm install && npm run build` (configured automatically via root `vercel.json`)
- **Output Directory**: `frontend/dist` (configured automatically via root `vercel.json`)

### Environment Variables on Vercel
The backend automatically detects the Vercel runtime and applies serverless defaults:
- `VISULOGIC_ENVIRONMENT`: defaults to `production`
- `VISULOGIC_DATABASE_URL`: defaults to `sqlite:////tmp/visulogic.db`
- `VISULOGIC_UPLOAD_DIR`: defaults to `/tmp/uploads`
- `VITE_API_BASE_URL`: defaults to `/api` (same origin) when deployed

*(Optional)* You can customize:
```text
VISULOGIC_ALLOWED_ORIGINS=["https://*.vercel.app"]
```

> [!NOTE]
> Serverless function containers on Vercel have ephemeral `/tmp` storage. Direct desktop uploads and analysis work within active containers. For multi-device QR mobile scans across distributed lambdas, Option 2 is recommended.

---

## Option 2: Decoupled Architecture (Recommended for Multi-Device QR Scans)

- **Frontend**: Vercel (Root Directory: `frontend`, Framework Preset: `Vite`, Build: `npm run build`, Output: `dist`, `VITE_API_BASE_URL=https://your-backend-host.example.com/api`).
- **Backend**: Render, Railway, Fly.io, or VPS with a persistent disk for SQLite and uploads.

On the persistent backend host, set:
```text
VISULOGIC_ENVIRONMENT=production
VISULOGIC_ALLOWED_ORIGINS=["https://your-vercel-app.vercel.app"]
VISULOGIC_DATABASE_URL=sqlite:////persistent/path/visulogic.db
VISULOGIC_UPLOAD_DIR=/persistent/path/uploads
```

---

## Verification After Deployment

1. Open your deployed Vercel domain (e.g. `https://visulogic.vercel.app`).
2. Test the backend health endpoint: `https://visulogic.vercel.app/api/health` -> should return `{"status":"ok",...}`.
3. Test upload: Upload `data/demo-flowchart.png` on the dashboard.
4. Verify analysis: Check that diagram classification, components, edges, issues, and What-If queries execute and return results.

