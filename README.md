# VisuLogic

VisuLogic is a hackathon MVP that converts uploaded or phone-captured technical diagrams into structured graph data, validates the structure, and explains issues with visual evidence.

## V1 Boundaries

- Light theme only
- No login or signup
- No payments
- Desktop-first analysis dashboard
- Phone capture through temporary QR sessions and a mobile browser
- Deterministic graph validation before AI explanations

## Project Structure

```text
frontend/   React + Vite TypeScript UI
backend/    FastAPI, SQLAlchemy, SQLite, CV/graph/AI pipeline
data/       Curated local test diagrams
uploads/    Temporary uploaded images
docs/       Project documentation notes
```

## Development Commands

Backend:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Backend health check: `GET http://127.0.0.1:8000/api/health`

## Verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

```powershell
cd frontend
npm.cmd run build
```

See `docs/deployment-demo.md` for the demo dataset, deployment settings, and runbook.
For Vercel frontend deployment, see `docs/vercel-deployment.md`.
