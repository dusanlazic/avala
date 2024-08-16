from jsonschema import validate, ValidationError
from .logs import logger


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
        logger.error("Error found in field <b>%s</>: %s" % (path, e.message))
        return False
