"""In-memory views reuse the public numerical loader without shared mutations."""

import pytest

from tools.ablation_db import SnapshotTools
from tools.tests.series_fixtures import snapshot


def test_in_memory_snapshot_is_copied_and_uses_existing_calculations():
    raw = snapshot()
    view = SnapshotTools.from_data(raw)
    raw["articles"][0]["experiments"][0]["colloids"][0]["measured_properties"][0][
        "value"
    ] = 999.0
    assert view.get_series("77-s1")["points"][0]["size"] == 10.0
    assert view.list_series(77)[0]["shape_primary"] == "increasing"
    assert view.list_series(99) == []


def test_in_memory_snapshot_does_not_bypass_header_validation():
    raw = snapshot()
    raw["units"]["pulse_energy"] = "mJ"
    with pytest.raises(ValueError, match="unit"):
        SnapshotTools.from_data(raw)
