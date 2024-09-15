from .decorator import Batching, TargetingStrategy, TickScope, exploit
from .main import Avala

AUTO = TargetingStrategy.AUTO
NOP_TEAM = TargetingStrategy.NOP_TEAM
OWN_TEAM = TargetingStrategy.OWN_TEAM

SINGLE = TickScope.SINGLE
LAST_N = TickScope.LAST_N

__all__ = [
    "Avala",
    "exploit",
    "TargetingStrategy",
    "AUTO",
    "NOP_TEAM",
    "OWN_TEAM",
    "Batching",
    "TickScope",
    "SINGLE",
    "LAST_N",
]
