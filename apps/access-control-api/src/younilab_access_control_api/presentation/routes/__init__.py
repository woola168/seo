from younilab_access_control_api.presentation.routes.auth import router as auth_router
from younilab_access_control_api.presentation.routes.authorization import (
    router as authorization_router,
)
from younilab_access_control_api.presentation.routes.health import (
    router as health_router,
)
from younilab_access_control_api.presentation.routes.me import router as me_router
from younilab_access_control_api.presentation.routes.management import (
    router as management_router,
)

__all__ = [
    "auth_router",
    "authorization_router",
    "health_router",
    "management_router",
    "me_router",
]
