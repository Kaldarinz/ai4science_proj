"""Small synthetic snapshot fixtures; no claims or hand labels."""

from copy import deepcopy


def scalar(value: float = 10., statistic: str | None = "mean", **changes) -> dict:
    """Construct one explicitly number-weighted TEM diameter scalar."""
    record = {
        "quantity": "geometric_diameter", "technique": "tem",
        "weighting_quantity": "particle_count", "value": value,
    }
    if statistic is not None:
        record["statistic"] = statistic
    return record | changes


def histogram(**changes) -> dict:
    """Construct unequal-width bars with arbitrary digitized counts."""
    return {
        "x_quantity": "geometric_diameter", "y_quantity": "particle_count",
        "technique": "tem", "sizes": [[1., 3.], [3., 7.], [7., 13.]],
        "size_counts": [2., 3., 1.],
    } | changes


def curve(**changes) -> dict:
    """Construct a density whose mean is 5.5 nm under the project rule."""
    return {
        "x_quantity": "geometric_diameter", "y_quantity": "particle_count",
        "technique": "tem", "x": [1., 2., 10.], "y": [1., 1., 1.],
    } | changes


def experiment(eid: int, value: float = 10., **changes) -> dict:
    """Construct an experiment differing only in pulse energy and size."""
    return {
        "id": eid, "article_id": 77, "laser": 4,
        "wavelength": 800., "pulse_duration": 100., "repetition_rate": 1000.,
        "pulse_energy": float(eid), "synthesis_medium": 10,
        "free_surf_entrance": True,
        "ablation": {"target": 1, "ablation_batch_setup": {"volume": 2., "duration": .1}},
        "colloids": [{"id": eid + 1000, "medium": 10,
                      "measured_properties": [scalar(value)]}],
    } | changes


def snapshot(experiments: list[dict] | None = None) -> dict:
    """Construct a loader-compatible gold-only snapshot with shared refs."""
    return {
        "format": 1, "filter": {"sole_target_material": "gold", "completed_only": True},
        "interval_unit": "h", "options": {},
        "units": {"fluence": "J/cm²", "pulse_energy": "μJ", "spot_diameter": "μm",
                  "wavelength": "nm", "pulse_duration": "fs", "particle_size": "nm",
                  "geometric_diameter": "nm", "hydrodynamic_diameter": "nm"},
        "parameter_quantities": {p: p for p in ("pulse_energy", "pulse_duration", "wavelength")},
        "field_units": {
            "experiments": {
                "pulse_fluence": {"quantity": "fluence"},
                "pulse_energy": {"parameter": "pulse_energy"},
                "pulse_duration": {"parameter": "pulse_duration"},
                "wavelength": {"parameter": "wavelength"},
                "spot_diameter": {"quantity": "spot_diameter"},
            },
            "colloids": {"storage_duration": "interval"},
            "measured_properties": {"value": {"field": "quantity"}},
            "size_distributions": {"sizes": {"field": "x_quantity"}},
            "measurement_curves": {"x": {"field": "x_quantity"}},
        },
        "articles": [{"id": 77, "title": "Synthetic example", "year": 2020,
                      "experiments": deepcopy(experiments) if experiments is not None else
                      [experiment(100, 10.), experiment(200, 20.), experiment(300, 30.)]}],
        "shared": {
            "targets": {"1": {"constituents": [{"material": 2, "fraction": 1.}]}},
            "materials": {"2": {"base_material": 3}},
            "base_materials": {"3": {"material": "Gold", "formula": "Au"}},
            "instruments": {"4": {"instrument_type": "laser"}},
            "liquid_media": {"10": {"constituents": [{"liquid": 11, "fraction": 1.}]}},
            "liquids": {"11": {"base_liquid": 12}},
            "base_liquids": {"12": {"liquid_name": "Water", "formula": "H2O"}},
        },
        "referenced_colloids": [],
    }
