game_schema = {
    "type": "object",
    "properties": {
        "tick_duration": {"type": "number", "exclusiveMinimum": 0},
        "flag_format": {"type": "string"},
        "team_ip": {
            "oneOf": [
                {"type": "string", "format": "hostname"},
                {"type": "array", "items": {"type": "string", "format": "hostname"}},
            ]
        },
        "start": {
            "type": "string",
            "pattern": "^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$",
        },
        "teams_json_url": {"type": "string", "format": "uri"},
        "teams_json_key": {"type": "string"},
        "team_ip_format": {"type": "string"},
    },
    "required": ["tick_duration", "flag_format", "team_ip"],
    "additionalProperties": False,
}

submitter_schema = {
    "type": "object",
    "properties": {
        "delay": {"type": "number", "exclusiveMinimum": 0},
        "interval": {"type": "number", "exclusiveMinimum": 0},
        "module": {"type": "string"},
    },
    "oneOf": [{"required": ["delay"]}, {"required": ["interval"]}],
    "additionalProperties": False,
}

server_schema = {
    "type": "object",
    "properties": {
        "host": {"type": "string", "format": "hostname"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "password": {"type": "string"},
    },
    "additionalProperties": False,
}

database_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "user": {"type": "string"},
        "password": {"type": "string"},
        "host": {"type": "string", "format": "hostname"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
    },
    "additionalProperties": False,
}

server_yaml_schema = {
    "type": "object",
    "properties": {
        "game": game_schema,
        "submitter": submitter_schema,
        "server": server_schema,
        "database": database_schema,
    },
    "required": ["game", "submitter"],
}
