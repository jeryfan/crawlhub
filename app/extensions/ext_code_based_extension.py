from core.extension.extension import Extension
from fastapi import FastAPI


def init_app(app: FastAPI):
    code_based_extension.init()


code_based_extension = Extension()
