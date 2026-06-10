import functools
import inspect
from typing import Callable

from fastapi import Depends, HTTPException, status

from core.deps import get_current_user
from users.models import User


def min_perms(min_role: int) -> Callable:
    """Декоратор: доступ только при role >= min_role."""

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role < min_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return user

    def decorator(endpoint: Callable) -> Callable:
        sig = inspect.signature(endpoint)
        params = [
            p for p in sig.parameters.values() if p.name != "current_user"
        ]
        params.append(
            inspect.Parameter(
                "current_user",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=User,
                default=Depends(checker),
            )
        )

        endpoint_sig = inspect.signature(endpoint)

        @functools.wraps(endpoint)
        async def wrapper(*args, **kwargs):
            kwargs.pop("current_user", None)
            bound = endpoint_sig.bind_partial(*args, **kwargs)
            return await endpoint(*bound.args, **bound.kwargs)

        wrapper.__signature__ = sig.replace(parameters=params)
        return wrapper

    return decorator
