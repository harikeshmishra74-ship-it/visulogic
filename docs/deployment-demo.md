# Deployment and Demo Runbook

## Runtime

- Backend: Python 3.12.x. The pinned OpenCV/NumPy stack is verified with Python 3.12; Python 3.14 may try to build NumPy from source.
- Frontend: Node.js with npm, using the committed `frontend/package-lock.json`.
- Storage: SQLite plus local upload directories for the MVP.

## Local Verification

Backend:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run build
```

Demo dataset:

```powershell
cd data
..\backend\.venv\Scripts\python.exe .\generate_demo_diagrams.py
```

## Demo Flow

1. Start the backend from `backend` with `.\.venv\Scripts\uvicorn.exe app.main:app --reload`.
2. Start the frontend from `frontend` with `npm.cmd run dev`.
3. Open `http://127.0.0.1:5173`.
4. Upload `data/demo-flowchart.png` or create a phone scan session and upload from the mobile page.
5. Confirm the dashboard shows classification, extracted elements, graph edges, structural issues, explanations, and What-If answers.

## Production Notes

- Set `VISULOGIC_ENVIRONMENT=production`.
- Set `VISULOGIC_ALLOWED_ORIGINS` to the deployed frontend origin list.
- Set `VISULOGIC_DATABASE_URL` and `VISULOGIC_UPLOAD_DIR` to persistent locations.
- Keep `VISULOGIC_MAX_UPLOAD_BYTES` and `VISULOGIC_MAX_IMAGE_PIXELS` conservative for the host size.
- Put FastAPI behind HTTPS and a reverse proxy that enforces request body limits.
- Do not persist demo uploads beyond the event unless users explicitly opt in.
