from enum import Enum


class TargetingStrategy(Enum):
    """
    Targeting strategy that can be used as an alternative to specifying a collection of targets in the exploit
    configuration.

    :cvar AUTO:
        Selects the available targets based on flag IDs provided by the game server, or all targets provided in the
        server configuration if the function does not take `flag_ids` argument.
    :cvar NOP_TEAM:
        Selects the hosts of the NOP team.
    :cvar OWN_TEAM:
        Selects the hosts of your own team.
    """

    AUTO = "auto"
    NOP_TEAM = "nop_team"
    OWN_TEAM = "own_team"


class FlagIdScope(Enum):
    """
    Enumeration representing the scope of ticks for which flag IDs are provided to the exploit function.

    :cvar SINGLE_TICK:
        `flag_ids` object will represent flag IDs relevant to a single service, target, and tick.
        When using `SINGLE_TICK`, each flag ID that successfully returns a flag will be tracked, allowing Avala client
        to skip the attacks that are using the same flag ID (based on exploit alias, target host and flag id value).
        This is the recommended and optimized approach.
    :cvar LAST_N_TICKS:
        `flag_ids` object will contain a list of flag IDs relevant to a single service, target, and the last N ticks.
        In most cases, not necessary and is inefficient due to performing redundant attacks.
    """

    SINGLE_TICK = "single"
    LAST_N_TICKS = "last_n"
