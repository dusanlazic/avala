from jsonschema import validate, ValidationError
from loguru import logger
from .logs import TextStyler as st


def validate_data(data, schema, custom=None):
    try:
        validate(instance=data, schema=schema)

        if callable(custom):
            custom(data)
        elif isinstance(custom, list) and all(callable(func) for func in custom):
            [func(data) for func in custom]

        return True
    except ValidationError as e:
        path = ".".join((str(x) for x in e.path))
        logger.error(f"Error found in field {st.bold(path)}: {e.message}")
        return False
