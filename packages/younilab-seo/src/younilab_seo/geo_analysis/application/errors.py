class GeoAnalysisApplicationError(Exception):
    """GEO orchestration use case 的基底錯誤。"""


class PublishFailed(GeoAnalysisApplicationError):
    """message broker 拒絕或派送失敗時拋出的錯誤。"""
