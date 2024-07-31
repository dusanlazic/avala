from .main import Avala
from .decorator import exploit, draft, TargetingStrategy, Batching

AUTO = TargetingStrategy.AUTO
NOP_TEAM = TargetingStrategy.NOP_TEAM
OWN_TEAM = TargetingStrategy.OWN_TEAM

__all__ = [
    "Avala",
    "exploit",
    "draft",
    "TargetingStrategy",
    "AUTO",
    "NOP_TEAM",
    "OWN_TEAM",
    "Batching",
]
