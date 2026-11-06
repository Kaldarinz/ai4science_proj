"""Small synthetic snapshot, independent of tools/tests and curated values."""

from copy import deepcopy


def experiment(eid: int, *, article_id: int = 77, wavelength: int | None = 532,
               technique: str | None = "tem", weighting: str | None = "particle_count",
               component: str | None = None, statistic: str = "mean") -> dict:
    """Make one gold-ablation experiment with a traceable scalar size."""
    record = {"quantity": "geometric_diameter", "statistic": statistic, "value": 10 + eid}
    record.update({k: v for k, v in (("technique", technique), ("weighting_quantity", weighting),
                                   ("component", component)) if v is not None})
    result = {
        "id": eid, "article_id": article_id, "laser": 1,
        "pulse_energy": eid * 10, "synthesis_medium": 7, "free_surf_entrance": True,
        "ablation": {"target": 2, "ablation_batch_setup": {"volume": 10, "duration": 1}},
        "colloids": [{"id": 1000 + eid, "medium": 7, "measured_properties": [record]}],
    }
    if wavelength is not None:
        result["wavelength"] = wavelength
    return result


def snapshot(experiments: list[dict] | None = None) -> dict:
    """Make schema-valid metadata and minimal shared contents from literals."""
    experiments = [experiment(1), experiment(2)] if experiments is None else experiments
    articles = {}
    for e in experiments:
        articles.setdefault(e["article_id"], {"id": e["article_id"], "title": "Synthetic", "experiments": []})["experiments"].append(deepcopy(e))
    return {
        "format": 1, "checkout_schema_change": "0095",
        "schema_metadata_hash": "c129120a031257f6e46e3a46d0762bef",
        "exported_at": "2026-10-27T00:00:00Z", "source": "test",
        "filter": {"sole_target_material": "gold", "completed_only": True},
        "options": {"include_manufacturers": False, "include_instrument_details": False,
                    "include_settings": False, "compact_materials": True,
                    "include_provenance": False, "omit_nulls": True},
        "interval_unit": "h",
        "units": {"fluence": "J/cm²", "pulse_energy": "μJ", "spot_diameter": "μm",
                  "pulse_duration": "fs", "wavelength": "nm", "geometric_diameter": "nm",
                  "hydrodynamic_diameter": "nm", "particle_size": "nm"},
        "parameter_quantities": {"pulse_energy": "pulse_energy", "pulse_duration": "pulse_duration", "wavelength": "wavelength"},
        "field_units": {
            "experiments": {"pulse_fluence": {"quantity": "fluence"}, "pulse_energy": {"parameter": "pulse_energy"},
                            "spot_diameter": {"quantity": "spot_diameter"}, "pulse_duration": {"parameter": "pulse_duration"},
                            "wavelength": {"parameter": "wavelength"}},
            "colloids": {"storage_duration": "interval"},
            "measured_properties": {"value": {"field": "quantity"}},
            "size_distributions": {"sizes": {"field": "x_quantity"}},
            "measurement_curves": {"x": {"field": "x_quantity"}},
        },
        "articles": list(articles.values()), "referenced_colloids": [],
        "shared": {
            "instruments": {"1": {"instrument_type": "laser"}},
            "targets": {"2": {"constituents": [{"material": 3, "fraction": 1}]}},
            "materials": {"3": {"base_material": 4}},
            "base_materials": {"4": {"material": "Gold", "formula": "Au"}},
            "base_liquids": {"5": {"liquid_name": "Water", "formula": "H2O"}},
            "liquids": {"6": {"base_liquid": 5}},
            "liquid_media": {"7": {"constituents": [{"liquid": 6, "fraction": 1}]}},
        },
    }
