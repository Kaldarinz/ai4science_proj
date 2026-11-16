"""Schema-guided article input projection; no numerical calculations.

Retain the chosen article, its reachable shared/document records, and global
interpretation headers. Other articles and unused shared records are omitted.
Export time is retained for schema validation but excluded from input bindings.
"""

from copy import deepcopy


def article_snapshot(snapshot, schema, article):
    """Return a standalone numerical view, following x-shared/x-document refs."""
    if type(article) is not int or article <= 0:
        raise ValueError("article must be a positive integer")
    selected = [
        row
        for row in snapshot["articles"]
        if isinstance(row, dict) and row.get("id") == article
    ]
    if len(selected) != 1:
        raise ValueError(f"expected exactly one snapshot article {article}")
    definitions = schema["$defs"]
    result = {
        key: deepcopy(value)
        for key, value in snapshot.items()
        if key not in {"articles", "shared", "referenced_colloids"}
    }
    result.update(articles=deepcopy(selected), shared={}, referenced_colloids=[])
    seen = set()

    def visit(value, specification):
        if "$ref" in specification:
            specification = definitions[specification["$ref"].rsplit("/", 1)[1]]
        if value is None:
            return
        if "x-shared" in specification:
            table = specification["x-shared"]
            key = (table, str(value))
            if key not in seen:
                seen.add(key)
                record = snapshot["shared"][table][str(value)]
                result["shared"].setdefault(table, {})[str(value)] = deepcopy(record)
                visit(record, definitions[table])
            return
        if specification.get("x-document") == "colloids":
            key = ("colloids", str(value))
            if key not in seen:
                seen.add(key)
                matches = [
                    record
                    for record in snapshot.get("referenced_colloids", [])
                    if isinstance(record, dict) and record.get("id") == value
                ]
                for item in snapshot["articles"]:
                    experiments = (
                        item.get("experiments", []) if isinstance(item, dict) else []
                    )
                    if not isinstance(experiments, list):
                        continue
                    for experiment in experiments:
                        colloids = (
                            experiment.get("colloids", [])
                            if isinstance(experiment, dict)
                            else []
                        )
                        if isinstance(colloids, list):
                            matches.extend(
                                record
                                for record in colloids
                                if isinstance(record, dict)
                                and record.get("id") == value
                            )
                if len(matches) != 1:
                    raise ValueError(f"missing/duplicate referenced colloid {value}")
                result["referenced_colloids"].append(deepcopy(matches[0]))
                visit(matches[0], definitions["colloids"])
            return
        if isinstance(value, list):
            for item in value:
                visit(item, specification.get("items", {}))
        elif isinstance(value, dict):
            properties = specification.get("properties", {})
            fallback = specification.get("additionalProperties", {})
            fallback = fallback if isinstance(fallback, dict) else {}
            for key, item in value.items():
                visit(item, properties.get(key, fallback))

    visit(selected, schema["properties"]["articles"])
    result["referenced_colloids"].sort(key=lambda row: row["id"])
    return result
