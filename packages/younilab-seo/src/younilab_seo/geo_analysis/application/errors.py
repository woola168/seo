class GeoAnalysisApplicationError(Exception):
    """GEO orchestration application use case 的共同錯誤基底。"""


class PublishFailed(GeoAnalysisApplicationError):
    """message broker 發布操作無法完成時使用的錯誤。"""


class ArchivedGeoQueryStatusError(GeoAnalysisApplicationError):
    """Archived Query 不可重新參與排程。"""

    def __init__(self) -> None:
        super().__init__("已下架的 Query 無法變更排程狀態")
