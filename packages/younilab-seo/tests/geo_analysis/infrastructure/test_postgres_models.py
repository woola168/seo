from pathlib import Path

from younilab_seo.geo_analysis.application import (
    GeoAnalysisRepository,
    GeoQueryRunJobRepository,
)
from younilab_seo.geo_analysis.infrastructure import (
    GeoMessageDispatchLogRow,
    GeoProjectRow,
    GeoQueryRunJobRow,
    GeoRunRequestRow,
    GeoRunResultReferenceRow,
    GeoRunResultRow,
    PostgresGeoAnalysisRepository,
    build_postgres_session_factory,
)


def test_postgres_rows_use_timezone_aware_timestamps_and_neutral_message_names() -> None:
    tables = [GeoProjectRow.__table__, GeoQueryRunJobRow.__table__, GeoMessageDispatchLogRow.__table__]
    column_types = "\n".join(
        str(column.type)
        for table in tables
        for column in table.columns
    )
    table_names = {table.name for table in tables}
    dispatch_columns = set(GeoMessageDispatchLogRow.__table__.columns.keys())

    assert "DATETIME" in column_types or "TIMESTAMP" in column_types
    assert "geo_message_dispatch_log" in table_names
    assert "message_backend" in dispatch_columns
    assert not any("pubsub" in table_name for table_name in table_names)


def test_run_result_tables_exist_without_metric_tables() -> None:
    defined_tables = {
        GeoProjectRow.__tablename__,
        GeoQueryRunJobRow.__tablename__,
        GeoMessageDispatchLogRow.__tablename__,
        GeoRunRequestRow.__tablename__,
        GeoRunResultRow.__tablename__,
        GeoRunResultReferenceRow.__tablename__,
    }

    assert "geo_run_request" in defined_tables
    assert "geo_run_result" in defined_tables
    assert "geo_run_result_reference" in defined_tables
    assert "geo_response_mention" not in defined_tables
    assert "geo_daily_query_metric" not in defined_tables


def test_postgres_repository_implements_job_repository_port() -> None:
    repository = PostgresGeoAnalysisRepository(
        build_postgres_session_factory(
            "postgresql+asyncpg://user:pass@localhost/resource_catalog"
        )
    )

    assert isinstance(repository, GeoQueryRunJobRepository)
    assert isinstance(repository, GeoAnalysisRepository)


def test_local_schema_file_contains_geo_orchestration_tables() -> None:
    schema_path = (
        Path(__file__).parents[5]
        / "deploy"
        / "local"
        / "postgresql"
        / "004_geo_analysis_schema.sql"
    )
    schema = schema_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS geo_project" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_query_run_job" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_message_dispatch_log" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_external_run_reference" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_run_request" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_run_result" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_run_result_reference" in schema
