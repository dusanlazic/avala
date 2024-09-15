from typing import Annotated

from fastapi import Depends

from .basic import get_current_user

CurrentUser = Annotated[str, Depends(get_current_user)]
