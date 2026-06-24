class GeoAnalysisApplicationError(Exception):
    """Base error for GEO orchestration application use cases."""


class PublishFailed(GeoAnalysisApplicationError):
    """Raised when a message broker publish operation cannot be completed."""
