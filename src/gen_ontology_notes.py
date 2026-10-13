"""Создаёт/обновляет заметки классов ontology/<Класс>.md из ontology.yaml."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ONT = ROOT / "ontology.yaml"
OUT = ROOT / "ontology"


def main() -> None:
    data = yaml.safe_load(ONT.read_text())
    classes = data["classes"]
    props = data["properties"]
    attrs = data["attributes"]

    # отношения и атрибуты по domain
    rel_by_domain: dict[str, list[str]] = {}
    for name, p in props.items():
        for d in p["domain"]:
            rel_by_domain.setdefault(d, []).append(name)
    attr_by_domain: dict[str, list[str]] = {}
    for name, a in attrs.items():
        for d in a["domain"]:
            attr_by_domain.setdefault(d, []).append(name)

    OUT.mkdir(exist_ok=True)
    for cls, info in classes.items():
        parent = info["parent"]
        rels = rel_by_domain.get(cls, [])
        attrs_c = attr_by_domain.get(cls, [])
        lines = [
            "---",
            "kind: класс",
            "---",
            f"# {cls}",
            "",
            info["definition"],
            "",
        ]
        if rels:
            lines.append("Отношения от этого класса: " + ", ".join(rels) + ".")
        else:
            lines.append("Отношения от этого класса: нет.")
        if attrs_c:
            vals = ", ".join(attrs_c)
            lines.append(f"Атрибуты: {vals}.")
        else:
            lines.append("Атрибуты: нет.")
        lines += ["", "## Связи"]
        if parent:
            lines.append(f"- подклассОт: [[{parent}]]")
        (OUT / f"{cls}.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(classes)} class notes to {OUT}")


if __name__ == "__main__":
    main()