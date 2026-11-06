"""Independent checks of METHOD.md §3; no production grouping helpers used.

The exported schema supplies reference types. Compatibility is checked by
exhaustive list matching, independently of the tools' bipartite matcher.
Every returned violation is fatal; there is no automatically learned allowlist.
"""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "data/ablation_snapshot.schema.json"
SNAPSHOT_PATH = ROOT / "data/ablation_snapshot.json"
SNAPSHOT_SHA256 = "c5380620d896237ad655bfde0ce166d3f638b84a3e9b0b996cc09226f6b8303f"
SIZE_QUANTITIES = {"geometric_diameter", "hydrodynamic_diameter", "particle_size"}
CONDITION_FIELDS = (
    "laser", "wavelength", "pulse_duration", "repetition_rate", "beam_diameter",
    "polarization", "spatial_mode", "beam_path", "ablation", "fragmentation",
    "feedstock", "synthesis_medium", "postprocessing_steps", "entrance_mat",
    "free_surf_entrance", "pumping_gas", "pumping_flow_rate", "pumping_duration",
    "pumping_during_processing",
)
OPTIONS = {
    "include_manufacturers": False, "include_instrument_details": False,
    "include_settings": False, "compact_materials": True,
    "include_provenance": False, "omit_nulls": True,
}


@dataclass(frozen=True)
class Violation:
    """A stable machine-readable rule name and an actionable location."""

    code: str
    path: str
    detail: str

    def as_dict(self) -> dict:
        """Return JSON-ready diagnostics."""
        return asdict(self)


def load_json(path: str | Path) -> dict:
    """Load JSON without silently admitting JavaScript nonfinite constants."""
    def reject(value: str) -> None:
        raise ValueError(f"nonfinite JSON constant: {value}")

    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject)


def finite(value: object) -> bool:
    """Recognize finite JSON numbers, excluding booleans."""
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def resolve(value: object, spec: dict, snapshot: dict, schema: dict, trail: tuple = ()) -> object:
    """Expand shared refs using x-shared schema annotations, retaining colloid ids."""
    if "$ref" in spec:
        spec = schema["$defs"][spec["$ref"].rsplit("/", 1)[1]]
    if value is None:
        return None
    if "x-shared" in spec:
        table = spec["x-shared"]
        identity = (table, str(value))
        if identity in trail:
            raise ValueError(f"cyclic reference {identity}")
        try:
            row = snapshot["shared"][table][str(value)]
        except KeyError as error:
            raise ValueError(f"missing reference {identity}") from error
        return resolve(row, schema["$defs"][table], snapshot, schema, (*trail, identity))
    if isinstance(value, list):
        return [resolve(v, spec.get("items", {}), snapshot, schema, trail) for v in value]
    if isinstance(value, dict):
        properties = spec.get("properties", {})
        fallback = spec.get("additionalProperties", {})
        fallback = fallback if isinstance(fallback, dict) else {}
        result = {k: resolve(v, properties.get(k, fallback), snapshot, schema, trail)
                  for k, v in value.items()}
        for field, ordinal in (("beam_path", "path_order"), ("postprocessing_steps", "step")):
            if isinstance(result.get(field), list):
                result[field].sort(key=lambda row: row[ordinal])
        return result
    return value


def profile(experiment: dict, colloid: dict, snapshot: dict, schema: dict) -> dict:
    """Reconstruct the documented positive list of fixed-condition fields."""
    fixed = {k: experiment[k] for k in CONDITION_FIELDS if k in experiment}
    result = resolve(fixed, schema["$defs"]["experiments"], snapshot, schema)
    result["medium"] = resolve(colloid.get("medium"), {"x-shared": "liquid_media"}, snapshot, schema)
    return result


def compatible(a: object, b: object, field: str = "") -> bool:
    """Independent wildcard oracle, including significant collection absence."""
    if isinstance(a, list) or isinstance(b, list):
        a, b = ([] if a is None else a), ([] if b is None else b)
        if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b):
            return False
        arrangements = itertools.permutations(b) if field in {"constituents", "additives", "feedstock"} else [b]
        return any(all(compatible(x, y) for x, y in zip(a, candidate, strict=True))
                   for candidate in arrangements)
    if a is None or b is None:
        return True
    if isinstance(a, dict) and isinstance(b, dict):
        return all(compatible(a.get(k), b.get(k), k) for k in a.keys() | b.keys())
    return a == b


def walk(value: object, path: str = "snapshot"):
    """Visit nested JSON objects, including shared particles and referenced stocks."""
    yield path, value
    if isinstance(value, dict):
        for k, child in value.items():
            yield from walk(child, f"{path}.{k}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from walk(child, f"{path}[{i}]")


def check_snapshot(snapshot: dict, schema: dict | None = None) -> list[Violation]:
    """Check schema, header, references, units, identities, targets and raw ranges."""
    schema = load_json(SCHEMA_PATH) if schema is None else schema
    errors = [Violation("schema_mismatch", "/".join(map(str, e.absolute_path)), e.message)
              for e in Draft202012Validator(schema).iter_errors(snapshot)]
    if errors:
        return errors

    def fail(code: str, path: str, detail: str) -> None:
        errors.append(Violation(code, path, detail))

    if (snapshot["format"] != 1 or snapshot["options"] != OPTIONS
            or snapshot["filter"] != {"sole_target_material": "gold", "completed_only": True}
            or snapshot["checkout_schema_change"] != "0095"
            or snapshot["schema_metadata_hash"] != "c129120a031257f6e46e3a46d0762bef"):
        fail("header_mismatch", "snapshot", "format/options/filter/schema version differ from METHOD §3")
    expected_units = {"fluence": "J/cm²", "pulse_energy": "μJ", "spot_diameter": "μm",
                      "pulse_duration": "fs", "wavelength": "nm"} | dict.fromkeys(SIZE_QUANTITIES, "nm")
    for quantity, unit in expected_units.items():
        if snapshot["units"].get(quantity) != unit:
            fail("unit_mismatch", f"units.{quantity}", f"expected {unit}")
    if snapshot["interval_unit"] != "h":
        fail("unit_mismatch", "interval_unit", "expected h")
    for parameter in ("pulse_energy", "pulse_duration", "wavelength"):
        if snapshot["parameter_quantities"].get(parameter) != parameter:
            fail("unit_mismatch", f"parameter_quantities.{parameter}", "wrong quantity route")
    routes = {
        ("experiments", "pulse_fluence"): {"quantity": "fluence"},
        ("experiments", "pulse_energy"): {"parameter": "pulse_energy"},
        ("experiments", "spot_diameter"): {"quantity": "spot_diameter"},
        ("experiments", "pulse_duration"): {"parameter": "pulse_duration"},
        ("experiments", "wavelength"): {"parameter": "wavelength"},
        ("colloids", "storage_duration"): "interval",
        ("measured_properties", "value"): {"field": "quantity"},
        ("size_distributions", "sizes"): {"field": "x_quantity"},
        ("measurement_curves", "x"): {"field": "x_quantity"},
    }
    for (table, column), expected in routes.items():
        if snapshot["field_units"].get(table, {}).get(column) != expected:
            fail("unit_mismatch", f"field_units.{table}.{column}", "wrong unit route")
    try:
        resolve(snapshot, schema, snapshot, schema)
    except ValueError as error:
        fail("broken_reference", "snapshot", str(error))
        return errors
    aids, eids = set(), set()
    for article in snapshot["articles"]:
        aid = article["id"]
        if aid <= 0 or aid in aids:
            fail("duplicate_article", f"article {aid}", "nonpositive or repeated article id")
        aids.add(aid)
        for e in article["experiments"]:
            path = f"article {aid}/experiment {e['id']}"
            if e["id"] <= 0 or e["id"] in eids:
                fail("duplicate_experiment", path, "nonpositive or repeated experiment id")
            eids.add(e["id"])
            if e["article_id"] != aid:
                fail("wrong_article", path, "article_id differs from containing article")
            for field, maximum in (("pulse_fluence", 1000), ("pulse_energy", 1e6)):
                if e.get(field) is not None and not (finite(e[field]) and 0 < e[field] <= maximum):
                    fail("out_of_range", f"{path}.{field}", f"requires 0 < value <= {maximum}")
            target_id = e.get("ablation", {}).get("target")
            target = snapshot["shared"].get("targets", {}).get(str(target_id), {})
            parts = target.get("constituents", [])
            gold = bool(parts)
            for part in parts:
                if "material" in part:
                    material_id = part["material"]
                else:
                    material_id = snapshot["shared"]["particles"][str(part["particle"])].get("material")
                material = snapshot["shared"].get("materials", {}).get(str(material_id), {})
                base = snapshot["shared"].get("base_materials", {}).get(str(material.get("base_material")), {})
                gold &= (base["formula"] == "Au" if base.get("formula") is not None
                         else base.get("material", "").casefold() in ("gold", "au"))
            if not gold:
                fail("non_gold_target", path, "target is not exclusively gold ablation")
    for path, value in walk(snapshot):
        if type(value) is float and not math.isfinite(value):
            fail("out_of_range", path, "nonfinite number")
        if not isinstance(value, dict) or path.startswith("snapshot.field_units"):
            continue
        for r in value.get("measured_properties", []):
            if r["quantity"] in SIZE_QUANTITIES:
                width = r["statistic"] in ("standard_deviation", "standard_error", "fwhm")
                if not (finite(r["value"]) and (r["value"] >= 0 if width else r["value"] > 0)):
                    fail("out_of_range", path, "invalid size statistic or width")
        for h in value.get("size_distributions", []):
            bars, counts = h["sizes"], h["size_counts"]
            good = bool(bars) and len(bars) == len(counts)
            previous = 0.
            for bar in bars:
                if not (isinstance(bar, list) and len(bar) == 2 and all(finite(v) for v in bar)):
                    good = False
                    break
                lo, hi = bar
                good &= 0 <= lo < hi and lo >= previous
                previous = hi
            good &= all(finite(c) and c >= 0 for c in counts) and any(finite(c) and c > 0 for c in counts)
            if not good:
                fail("bad_bins", path, "bars/counts must align, ascend, not overlap and have positive total mass")
            if h.get("particles_counted") is not None and h["particles_counted"] <= 0:
                fail("out_of_range", path, "particles_counted must be positive")
        for c in value.get("measurement_curves", []):
            if c["x_quantity"] not in SIZE_QUANTITIES:
                continue
            x, y = c["x"], c["y"]
            good = len(x) >= 2 and len(x) == len(y) and all(finite(v) and v >= 0 for v in x + y)
            if good:
                diffs = [b - a for a, b in itertools.pairwise(x)]
                good = (all(d > 0 for d in diffs) or all(d < 0 for d in diffs)) and any(v > 0 for v in y)
            if not good:
                fail("bad_curve", path, "size curve needs monotone diameter and nonnegative density with positive area")
    return errors


def measurement_identity(record: dict, source: str) -> tuple:
    """Read exact physical measurement labels, independently of tools.SizeKind."""
    scalar = source == "scalar"
    return (record.get("quantity" if scalar else "x_quantity"), record.get("technique"),
            record.get("weighting_quantity" if scalar else "y_quantity"), record.get("component"))


def check_series(snapshot: dict, data: dict, schema: dict | None = None, *, model: str = "primary") -> list[Violation]:
    """Check a public get_series response against raw members, not cached keys."""
    schema = load_json(SCHEMA_PATH) if schema is None else schema
    row, points = data["series"], data["points"]
    errors = []

    def fail(code: str, detail: str) -> None:
        errors.append(Violation(code, row.get("series_id", "series"), detail))

    members = {e["id"]: (a["id"], e) for a in snapshot["articles"] for e in a["experiments"]}
    ids = [p["experiment_id"] for p in points]
    if len(set(ids)) != len(ids):
        fail("duplicate_point", "experiment repeated within one series")
    if len(points) < 2 or row["n_points"] != len(points) or len({p["x"] for p in points}) != len(points):
        fail("short_series", "point count or distinct x requirement failed")
    conditions = []
    selected = []
    for p in points:
        member = members.get(p["experiment_id"])
        if member is None or member[0] != row["article_id"]:
            fail("key_mismatch", "point is absent or belongs to another article")
            continue
        e = member[1]
        cs = [c for c in e.get("colloids", []) if c["id"] == p["colloid_id"]]
        if len(cs) != 1:
            fail("key_mismatch", "colloid is not a unique product of this experiment")
            continue
        c = cs[0]
        conditions.append(profile(e, c, snapshot, schema))
        selected.append(e)
        if c.get("storage_duration") != row["storage_duration_h"]:
            fail("key_mismatch", "storage duration differs; unknown is not zero or a wildcard")
        source_table = {"scalar": "measured_properties", "histogram": "size_distributions", "curve": "measurement_curves"}
        records = c.get(source_table.get(p["size_source"], ""), [])
        identity = tuple(row[k] for k in ("size_quantity", "size_technique", "size_weighting", "size_component"))
        matches = [r for r in records if measurement_identity(r, p["size_source"]) == identity]
        if p["size_source"] == "scalar":
            aliases = {None: "mean", "z_average": "mean", "peak": "mode"}
            matches = [r for r in matches if aliases.get(r.get("statistic"), r.get("statistic")) == row["size_statistic"]]
            if len(matches) == 1 and p["size"] != matches[0]["value"]:
                fail("value_mismatch", "selected scalar value differs from snapshot")
        if len(matches) != 1 or row["size_statistic"] not in ("mean", "median", "mode"):
            fail("key_mismatch", "source measurement does not match exact kind/statistic")
        if not (finite(p["size"]) and p["size"] > 0 and finite(p["size_err"]) and p["size_err"] >= 0):
            fail("out_of_range", "invalid selected size or error")
        if p.get("sd") is not None and not (finite(p["sd"]) and p["sd"] >= 0):
            fail("out_of_range", "invalid point SD")
        ns = {h["particles_counted"] for h in c.get("size_distributions", [])
              if h.get("particles_counted") is not None and measurement_identity(h, "histogram") == identity}
        expected_n = next(iter(ns)) if len(ns) == 1 else None
        if expected_n != p.get("particles_counted"):
            fail("value_mismatch", "N is not the uniquely reported matching particle count")
        widths = [r for r in c.get("measured_properties", [])
                  if measurement_identity(r, "scalar") == identity]
        sds = [r["value"] for r in widths if r["statistic"] == "standard_deviation"]
        ses = [r["value"] for r in widths if r["statistic"] == "standard_error"]
        sd = sds[0] if len(sds) == 1 else None
        if sd is None and len(matches) == 1 and p["size_source"] == "histogram":
            h = matches[0]
            centres = [(lo + hi) / 2 for lo, hi in h["sizes"]]
            mass = math.fsum(h["size_counts"])
            mean = math.fsum(x * w for x, w in zip(centres, h["size_counts"], strict=True)) / mass
            sd = math.sqrt(math.fsum(w * (x - mean) ** 2 for x, w in zip(centres, h["size_counts"], strict=True)) / mass)
        if sd is None and len(matches) == 1 and p["size_source"] == "curve":
            pairs = sorted(zip(matches[0]["x"], matches[0]["y"], strict=True))

            def integral(terms: list[float], positions: list = pairs) -> float:
                return math.fsum((b[0] - a[0]) * (u + v) / 2
                                 for (a, b), (u, v) in zip(itertools.pairwise(positions), itertools.pairwise(terms), strict=True))

            area = integral([y for x, y in pairs])
            mean = integral([x * y for x, y in pairs]) / area
            sd = math.sqrt(integral([(x - mean) ** 2 * y for x, y in pairs]) / area)
        if (sd is None) != (p.get("sd") is None) or (sd is not None and not math.isclose(sd, p["sd"], rel_tol=1e-12, abs_tol=1e-12)):
            fail("value_mismatch", "SD differs from stored width or independent distribution moment")
        if row["size_statistic"] == "mean" and len(ses) == 1:
            error, source = ses[0], "reported_se"
        elif row["size_statistic"] == "mean" and sd is not None and expected_n is not None:
            error, source = sd / math.sqrt(expected_n), "sd_over_sqrt_n"
        else:
            error, source = {"primary": .10, "lenient": .20}[model] * p["size"], "fallback"
        if p["err_source"] != source or not math.isclose(p["size_err"], error, rel_tol=1e-12, abs_tol=1e-12):
            fail("value_mismatch", "error value/source violates SE → mean SD/√N → fallback priority")
    for a, b in itertools.combinations(conditions, 2):
        if not compatible(a, b):
            fail("key_mismatch", "conflicting stated fixed conditions or collection presence")
            break
    if selected:
        expected = "fluence" if all(e.get("pulse_fluence") is not None for e in selected) else "pulse_energy"
        field = "pulse_fluence" if expected == "fluence" else "pulse_energy"
        if row["x_quantity"] != expected or any(e.get(field) != p["x"] for e, p in zip(selected, points, strict=False)):
            fail("mixed_x", "wrong x quantity, incomplete x or value differs from raw experiment")
        maximum = 1000 if expected == "fluence" else 1e6
        if any(not (finite(p["x"]) and 0 < p["x"] <= maximum) for p in points):
            fail("out_of_range", "x out of the declared range")
        if [p["x"] for p in points] != sorted(p["x"] for p in points):
            fail("mixed_x", "points are not sorted by x")
    return errors
