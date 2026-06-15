from younilab_resource_catalog_api.presentation.http.routes.customers import (
    router as customers_router,
)
from younilab_resource_catalog_api.presentation.http.routes.tasks import (
    router as tasks_router,
)

__all__ = ["customers_router", "tasks_router"]
