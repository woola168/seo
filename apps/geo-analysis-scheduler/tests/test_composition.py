from datetime import time

import pytest

from younilab_geo_analysis_scheduler.composition import _daily_time


def test_daily_time_uses_fixed_hour_and_minute() -> None:
    assert _daily_time("03:00") == time(3, 0)


@pytest.mark.parametrize("value", ["3", "24:00", "03:60", "bad"])
def test_daily_time_rejects_invalid_values(value: str) -> None:
    with pytest.raises(RuntimeError):
        _daily_time(value)
