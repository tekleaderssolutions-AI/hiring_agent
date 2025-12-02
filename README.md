# Recruitment AI (Django)

This repository was converted to a minimal Django project that serves the previously-built FastAPI endpoints as Django views and exposes a small frontend UI.

Quick start (PowerShell):

1. Create a virtualenv and install dependencies:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r .\requirements.txt
```

2. Ensure your Postgres server is running and the environment variables in `.env` (or `env.template`) are set.

3. Run the Django development server:

```powershell
python manage.py runserver 0.0.0.0:8000
```

4. Open http://localhost:8000/ to access the UI. Use the **Initialize Database** button to run the `vector` extension and create tables (requires DB user able to create extensions).

Notes:
- The management command `python manage.py init_db` also runs the DB initialization.
- The `/init-db` endpoint is unprotected in this minimal example — secure it before production use.
