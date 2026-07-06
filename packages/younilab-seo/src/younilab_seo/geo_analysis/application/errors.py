class GeoAnalysisApplicationError(Exception):
    """GEO orchestration application use case 的共同錯誤基底。"""


class PublishFailed(GeoAnalysisApplicationError):
    """message broker 發布操作無法完成時使用的錯誤。"""
