from younilab_seo.geo_analysis.infrastructure import (
    GeoMessageDispatchLogRow,
    GeoProjectRow,
    GeoQueryRunJobRow,
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


def test_no_ai_response_or_metric_tables_are_defined() -> None:
    defined_tables = {
        GeoProjectRow.__tablename__,
        GeoQueryRunJobRow.__tablename__,
        GeoMessageDispatchLogRow.__tablename__,
    }

    assert "geo_ai_response" not in defined_tables
    assert "geo_response_mention" not in defined_tables
    assert "geo_daily_query_metric" not in defined_tables
