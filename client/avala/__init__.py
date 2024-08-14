from .main import Avala
from .decorator import exploit, draft, TargetingStrategy, TickScope, Batching

AUTO = TargetingStrategy.AUTO

SINGLE = TickScope.SINGLE
LAST_N = TickScope.LAST_N

__all__ = [
    "Avala",
    "exploit",
    "draft",
    "TargetingStrategy",
    "AUTO",
    "Batching",
    "TickScope",
    "SINGLE",
    "LAST_N",
]
