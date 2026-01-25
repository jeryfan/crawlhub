import os
import time

from fastapi import FastAPI


def init_app(app: FastAPI):
    os.environ["TZ"] = "UTC"
    # windows platform not support tzset
    if hasattr(time, "tzset"):
        time.tzset()
