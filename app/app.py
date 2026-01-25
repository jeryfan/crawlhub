import uvicorn

from app_factory import create_app

app = create_app()

celery = app.state.celery
