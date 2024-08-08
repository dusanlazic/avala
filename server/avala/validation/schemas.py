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
        "nop_team_ip": {"type": "string", "format": "hostname"},
        "flag_ttl": {"type": "integer", "minimum": 1},
        "game_starts_at": {
            "type": "string",
            "pattern": "^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$",
        },
        "networks_open_after": {
            "type": "object",
            "properties": {
                "hours": {"type": "integer", "minimum": 0},
                "minutes": {"type": "integer", "minimum": 0},
                "seconds": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
            "minProperties": 1,
        },
        "game_ends_after": {
            "type": "object",
            "properties": {
                "hours": {"type": "integer", "minimum": 0},
                "minutes": {"type": "integer", "minimum": 0},
                "seconds": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
            "minProperties": 1,
        },
    },
    "required": ["tick_duration", "flag_format", "team_ip"],
    "additionalProperties": False,
}

submitter_schema = {
    "type": "object",
    "properties": {
        "module": {"type": "string"},
        "interval": {"type": "number", "exclusiveMinimum": 0},
        "per_tick": {"type": "integer", "minimum": 1},
        "batch_size": {"type": "integer", "minimum": 1},
        "max_batch_size": {"type": "integer", "minimum": 0},
        "streams": {"type": "integer", "minimum": 1},
    },
    "oneOf": [
        {"required": ["interval", "max_batch_size"]},
        {"required": ["per_tick", "max_batch_size"]},
        {"required": ["batch_size"]},
        {"required": ["streams"]},
    ],
    "additionalProperties": False,
}

attack_data_schema = {
    "type": "object",
    "properties": {
        "module": {"type": "string"},
        "max_attempts": {"type": "integer", "minimum": 1},
        "retry_interval": {"type": "number", "exclusiveMinimum": 0},
    },
    "additionalProperties": False,
}

server_schema = {
    "type": "object",
    "properties": {
        "host": {"type": "string", "format": "hostname"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "password": {"type": "string"},
        "cors": {"type": "array", "items": {"type": "string"}},
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

rabbitmq_schema = {
    "type": "object",
    "properties": {
        "host": {"type": "string", "format": "hostname"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "user": {"type": "string"},
        "password": {"type": "string"},
    },
    "additionalProperties": False,
}

server_yaml_schema = {
    "type": "object",
    "properties": {
        "game": game_schema,
        "submitter": submitter_schema,
        "attack_data": attack_data_schema,
        "server": server_schema,
        "database": database_schema,
        "rabbitmq": rabbitmq_schema,
    },
    "required": ["game", "submitter"],
}
