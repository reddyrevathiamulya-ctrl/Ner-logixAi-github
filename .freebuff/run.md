# NER-LogixAI — how to run

## Reproduce the artifacts

This is a Python FastAPI backend with a static frontend. No build artifacts
or env files are required to run it.

- Python 3.11 virtualenv at the repo root: `.venv` (has `fastapi`, `uvicorn`,
  `requests`, `ollama` — matches `backend/requirements.txt`).
- There is also a `backend/venv` that is missing `ollama`; use the root `.venv`.
- Data files are already committed under `backend/data/raw/` and
  `backend/data/processed/`; no download step is needed to start the API.

## Run the server

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The dashboard is served at `http://127.0.0.1:8000/`. It embeds the GIS
dashboard from `mobile/web/ml/gis/index.html`.

Health check: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`.

## Detached (preview) start

```powershell
powershell -NoProfile -Command "(Start-Process -FilePath '<repo>\.venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','backend.main:app','--reload','--host','127.0.0.1','--port','8000' -WorkingDirectory '<repo>' -RedirectStandardOutput '<repo>\.freebuff\preview.log' -RedirectStandardError '<repo>\.freebuff\preview.log.err' -WindowStyle Hidden -PassThru).Id"
```

Note: the shell call may appear to hang — the process survives; confirm via
`netstat -ano | grep :8000` and poll `http://127.0.0.1:8000/health`.