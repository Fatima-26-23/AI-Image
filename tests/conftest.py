import os
import sys

# So `from app...` imports work when pytest is run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# These tests never touch a real DB or network -- but app.config.Settings()
# reads .env / env vars at import time, so give it a harmless DATABASE_URL
# if none is set, purely so import doesn't fail on a clean CI machine
# without a .env file.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/flyrank_capstone")
