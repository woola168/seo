from younilab_seo.geo_analysis.application.contracts import GeoProjectRecord
from younilab_seo.geo_analysis.application.interfaces import AuthorizedPrincipal


def can_access_project(
    principal: AuthorizedPrincipal,
    project: GeoProjectRecord,
) -> bool:
    """判斷目前 principal 是否能存取指定 GEO project。"""

    if project.tenant_id != principal.tenant_id:
        return False
    if principal.has_global_resource_access:
        return True
    if project.customer_id is not None and project.customer_id in principal.customer_ids:
        return True
    return project.seo_task_id is not None and project.seo_task_id in principal.task_ids


def filter_accessible_projects(
    principal: AuthorizedPrincipal,
    projects: list[GeoProjectRecord],
) -> list[GeoProjectRecord]:
    """依 tenant 與 customer/task grants 過濾可見的 GEO projects。"""

    return [project for project in projects if can_access_project(principal, project)]
