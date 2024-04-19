from jsonschema import ValidationError


def validate_delay(server_yaml_data):
    if server_yaml_data["submitter"].get("delay") is None:
        return

    tick_duration = server_yaml_data["game"]["tick_duration"]
    delay = server_yaml_data["submitter"]["delay"]

    if delay >= tick_duration:
        raise ValidationError(
            f"Submitter delay ({delay}s) takes longer than the tick itself ({tick_duration}s).",
            path=["submitter", "delay"],
        )


def validate_interval(server_yaml_data):
    if server_yaml_data["submitter"].get("interval") is None:
        return

    interval = server_yaml_data["submitter"]["interval"]
    duration = server_yaml_data["game"]["tick_duration"]

    if duration % interval != 0:
        raise ValidationError(
            f"Tick duration ({duration}s) must be a multiple of the submitter interval ({interval}s).",
            path=["submitter", "interval"],
        )
