"""Read-only project API over a committed JSON snapshot, never a database.

Example (run from the project root)::

    from tools.ablation_db import list_series, get_series
    rows = list_series(80094)
    points = get_series(rows[0]["series_id"], model="lenient")["points"]

SnapshotTools(path) fixes one loaded snapshot for repeated calls. Module
functions reload the default path on each call, with no global cache.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

from tools.series import SIZE_QUANTITIES, BuildResult, build_series, validate_model

SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "ablation_snapshot.json"


def _validate_snapshot(snapshot: dict) -> None:
    """Reject incompatible headers, identifiers and physical units.

    This is loader validation, not the future HW2 data-contract verifier.
    Per-measurement numerical failures are exposed as exclusions.
    """
    if not isinstance(snapshot, dict) or type(snapshot.get("format")) is not int or snapshot["format"] != 1:
        raise ValueError("expected snapshot format 1")
    if snapshot.get("filter") != {"sole_target_material": "gold", "completed_only": True}:
        raise ValueError("expected a completed, gold-only snapshot")
    if snapshot.get("interval_unit") != "h":
        raise ValueError("snapshot intervals must be in hours")
    units = snapshot.get("units", {})
    required_units = {
        "fluence": "J/cm²", "pulse_energy": "μJ", "spot_diameter": "μm",
        "pulse_duration": "fs", "wavelength": "nm",
    }
    required_units.update({q: "nm" for q in SIZE_QUANTITIES if q in units})
    for quantity, unit in required_units.items():
        if units.get(quantity) != unit:
            raise ValueError(f"unsupported unit for {quantity}: {units.get(quantity)!r}; expected {unit}")
    parameter_quantities = snapshot.get("parameter_quantities", {})
    for parameter in ("pulse_energy", "pulse_duration", "wavelength"):
        if parameter_quantities.get(parameter) != parameter:
            raise ValueError(f"unsupported quantity for parameter {parameter}")
    field_units = snapshot.get("field_units", {})
    routes = {
        ("experiments", "pulse_fluence"): {"quantity": "fluence"},
        ("experiments", "pulse_energy"): {"parameter": "pulse_energy"},
        ("experiments", "pulse_duration"): {"parameter": "pulse_duration"},
        ("experiments", "wavelength"): {"parameter": "wavelength"},
        ("experiments", "spot_diameter"): {"quantity": "spot_diameter"},
        ("colloids", "storage_duration"): "interval",
        ("measured_properties", "value"): {"field": "quantity"},
        ("size_distributions", "sizes"): {"field": "x_quantity"},
        ("measurement_curves", "x"): {"field": "x_quantity"},
    }
    for (table, column), route in routes.items():
        if field_units.get(table, {}).get(column) != route:
            raise ValueError(f"unsupported unit route for {table}.{column}")
    if not isinstance(snapshot.get("shared"), dict) or not isinstance(snapshot.get("articles"), list):
        raise ValueError("snapshot needs shared objects and an article list")  # noqa: TRY004 -- malformed document
    article_ids, experiment_ids = set(), set()
    for article in snapshot["articles"]:
        aid = article["id"]
        if type(aid) is not int or aid <= 0 or aid in article_ids:
            raise ValueError(f"invalid or duplicate article id {aid!r}")
        article_ids.add(aid)
        for experiment in article["experiments"]:
            eid = experiment["id"]
            if type(eid) is not int or eid <= 0 or eid in experiment_ids:
                raise ValueError(f"invalid or duplicate experiment id {eid!r}")
            experiment_ids.add(eid)
            if experiment["article_id"] != aid:
                raise ValueError(f"experiment {eid} belongs to the wrong article")
            for colloid in experiment.get("colloids", []):
                for key, field in (("measured_properties", "quantity"),
                                   ("size_distributions", "x_quantity"),
                                   ("measurement_curves", "x_quantity")):
                    for record in colloid.get(key, []):
                        quantity = record[field]
                        if quantity in SIZE_QUANTITIES and units.get(quantity) != "nm":
                            raise ValueError(f"missing nm unit for size quantity {quantity}")


class SnapshotTools:
    """A fixed snapshot view with pure per-article calculations."""

    def __init__(self, path: str | Path | None = None) -> None:
        """Load and validate exactly the given path; never contact a server."""
        self.path = Path(path) if path is not None else SNAPSHOT_PATH
        # JSON permits NaN by default; snapshot numbers must be finite.
        def reject_constant(value: str) -> None:
            """Reject JavaScript non-finite constants in otherwise valid JSON."""
            raise ValueError(f"non-finite JSON constant {value}")

        self._snapshot = json.loads(
            self.path.read_text(encoding="utf-8"), parse_constant=reject_constant)
        _validate_snapshot(self._snapshot)
        self._built: dict[int, BuildResult] = {}

    def _article(self, article_id: int) -> BuildResult:
        """Build once per article in this explicitly fixed snapshot view."""
        if type(article_id) is not int or article_id <= 0:
            raise ValueError("article_id must be a positive integer")
        if article_id not in self._built:
            self._built[article_id] = build_series(self._snapshot, article_id)
        return self._built[article_id]

    def find_articles(self, material: str = "Au") -> list[dict]:
        """List gold-snapshot articles, including those without series."""
        if material not in ("Au", "gold"):
            raise ValueError("this snapshot supports only Au/gold")
        return [
            {"article_id": a["id"], "doi": a.get("doi"), "title": a["title"],
             "year": a.get("year"), "n_experiments": len(a["experiments"])}
            for a in sorted(self._snapshot["articles"], key=lambda a: a["id"])
        ]

    def list_series(self, article_id: int) -> list[dict]:
        """Return independent summaries; series may share experiments.

        Missing fixed-condition details are wildcards. An unknown may join
        several compatible groups without bridging known conflicts; notes
        mark such reused experiments with ``overlapping_series``.
        """
        return [deepcopy(s.row) for s in self._article(article_id).series]

    def get_series(self, series_id: str, model: str = "primary") -> dict:
        """Return a series and its points under the requested error model."""
        validate_model(model)
        match = re.fullmatch(r"([1-9][0-9]*)-s([1-9][0-9]*)", series_id) if isinstance(series_id, str) else None
        if match is None:
            raise ValueError("series_id must have the form <article_id>-s<positive index>")
        for series in self._article(int(match[1])).series:
            if series.row["series_id"] == series_id:
                return {"series": deepcopy(series.row), "points": series.points(model)}
        raise KeyError(series_id)

    def list_exclusions(self, article_id: int) -> list[dict]:
        """Return explicit reasons for unusable measurements and groups."""
        return deepcopy(self._article(article_id).exclusions)


def find_articles(material: str = "Au") -> list[dict]:
    """List articles from a fresh read of the default snapshot."""
    return SnapshotTools().find_articles(material)


def list_series(article_id: int) -> list[dict]:
    """List series from a fresh read of the default snapshot."""
    return SnapshotTools().list_series(article_id)


def get_series(series_id: str, model: str = "primary") -> dict:
    """Return points with model-specific errors from the default snapshot."""
    return SnapshotTools().get_series(series_id, model)


def list_exclusions(article_id: int) -> list[dict]:
    """List exclusions from a fresh read of the default snapshot."""
    return SnapshotTools().list_exclusions(article_id)
