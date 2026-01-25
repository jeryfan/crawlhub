from fastapi import FastAPI


def init_app(app: FastAPI):
    from events import event_handlers  # noqa: F401 # pyright: ignore[reportUnusedImport]
