from enum import Enum


class TargetingStrategy(Enum):
    """
    Targeting strategy that can be used as an alternative to specifying a list of targets in the exploit configuration.

    When using `TargetingStrategy.AUTO`, the exploit function **MUST** take the `flag_ids` argument, and the targeted service
    **MUST** be defined in the `attacks.json` or `teams.json` provided by the game server. This is essential because
    automatic targeting relies on fetching the list of targets from these files.

    :cvar AUTO:
        Selects the available targets based on `attacks.json` or `teams.json` files provided by the game server.
        The exploit function **MUST** take the `flag_ids` argument, and the targeted service **MUST** be defined in
        the `attacks.json` or `teams.json` provided by the game server.
    :cvar NOP_TEAM:
        Selects the IP or hostname of the NOP team.
    :cvar OWN_TEAM:
        Selects the IP or hostname of your own team.
    """

    AUTO = "auto"
    NOP_TEAM = "nop_team"
    OWN_TEAM = "own_team"


class TickScope(Enum):
    """
    Enumeration representing the scope of ticks for which flag IDs are provided to the exploit function.

    :cvar SINGLE:
        Specifies that the `flag_ids` object will contain only the flag IDs relevant to a single service, target, and tick.
        When using `SINGLE`, each flag ID that successfully returns a flag will be tracked and skipped in subsequent attempts,
        reducing the total number of attacks. This is the recommended approach.
    :cvar LAST_N:
        Specifies that the `flag_ids` object will contain a list of all flag IDs provided by the game server for the last N ticks.
    """

    SINGLE = "single"
    LAST_N = "last_n"
