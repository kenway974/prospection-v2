"""Point d'entrée de production : `uvicorn prospection.ui.main:app`."""

from prospection.config import load_settings
from prospection.storage.db import make_engine
from prospection.ui.app import create_app

settings = load_settings()
app = create_app(settings, make_engine(settings.database_url))
