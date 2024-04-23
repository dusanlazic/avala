from loguru import logger
from importlib import import_module, reload
from .models import Flag
from .config import config


def import_function():
    module_name = config["submitter"]["module"]

    imported_module = reload(import_module(module_name))
    submit_function = getattr(imported_module, "submit")

    return submit_function


def persist(submitted_flags):
    while True:
        value, status, response = submitted_flags.get()

        Flag.update(status=status, response=response).where(
            Flag.value == value
        ).execute()


def run():
    # Queue can be clogged if there is to many flags to submit and submitting service is too slow!
    # If flag checking service is REST API, you should be able to limit how many flags per request.
    flags = [flag.value for flag in Flag.select().where(Flag.status == "queued")]

    if config["submitter"]["processing_mode"] == "batch":
        pass
