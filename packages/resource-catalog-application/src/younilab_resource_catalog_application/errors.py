class ResourceCatalogError(Exception):
    pass


class ResourceNotFound(ResourceCatalogError):
    pass


class Conflict(ResourceCatalogError):
    pass


class AccessDenied(ResourceCatalogError):
    pass
