from fastapi import FastAPI


def init_app(app: FastAPI):
    import warnings

    warnings.simplefilter("ignore", ResourceWarning)
