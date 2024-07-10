connect_schema = {
    "type": "object",
    "properties": {
        "protocol": {"type": "string", "enum": ["http", "https"]},
        "host": {
            "type": "string",
            "format": "hostname",
        },
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "username": {"type": "string", "maxLength": 20},
        "password": {"type": "string"},
    },
    "additionalProperties": False,
}

manager_schema = {
    "type": "object",
    "properties": {
        "enabled": {"type": "boolean"},
        "host": {
            "type": "string",
            "format": "hostname",
        },
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "password": {"type": "string"},
    },
    "additionalProperties": False,
}

exploit_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "maxLength": 100,
        },
        "targets": {
            "type": "array",
            "items": {"type": "string"},
        },
        "skip": {
            "type": "array",
            "items": {"type": "string"},
        },
        "service": {
            "type": "string",
        },
        "module": {
            "type": "string",
        },
        "command": {
            "type": "string",
        },
        "prepare": {
            "type": "string",
        },
        "cleanup": {
            "type": "string",
        },
        "env": {
            "type": "object",
            "patternProperties": {".*": {"type": "string"}},
        },
        "delay": {
            "type": "integer",
            "minimum": 0,
        },
        "batching": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "minimum": 1},
                "size": {"type": "integer", "minimum": 1},
                "gap": {"type": "number", "exclusiveMinimum": 0},
            },
            "oneOf": [
                {"required": ["gap", "count"], "not": {"required": ["size"]}},
                {"required": ["gap", "size"], "not": {"required": ["count"]}},
            ],
        },
        "timeout": {
            "type": "integer",
            "exclusiveMinimum": 0,
        },
    },
    # "oneOf": [
    #     {"required": ["name", "targets"], "not": {"required": ["service"]}},
    #     {"required": ["name", "service"], "not": {"required": ["targets"]}},
    # ],
    "additionalProperties": False,
}

exploits_schema = {
    "type": ["array", "null"],
    "items": exploit_schema,
}

defaults_schema = {
    "type": "object",
    "properties": {
        "targets": {
            "type": "array",
            "items": {"type": "string"},
        },
        "skip": {
            "type": "array",
            "items": {"type": "string"},
        },
        "prepare": {
            "type": "string",
        },
        "cleanup": {
            "type": "string",
        },
        "env": {
            "type": "object",
            "patternProperties": {".*": {"type": "string"}},
        },
        "delay": {
            "type": "integer",
            "minimum": 0,
        },
        "batching": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "minimum": 1},
                "size": {"type": "integer", "minimum": 1},
                "gap": {"type": "number", "exclusiveMinimum": 0},
            },
            "oneOf": [
                {"required": ["gap", "count"], "not": {"required": ["size"]}},
                {"required": ["gap", "size"], "not": {"required": ["count"]}},
            ],
        },
        "timeout": {
            "type": "integer",
            "exclusiveMinimum": 0,
        },
    },
    "additionalProperties": False,
}

client_yaml_schema = {
    "type": "object",
    "properties": {
        "connect": connect_schema,
        "manager": manager_schema,
        "exploits": exploits_schema,
        "default": defaults_schema,
    },
    "required": ["connect", "exploits"],
}
