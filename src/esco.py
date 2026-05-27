from __future__ import annotations

import ast
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for si in root.findall("a:si", NS):
        strings.append("".join(t.text or "" for t in si.findall(".//a:t", NS)))
    return strings


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    value = cell.find("a:v", NS)
    if value is None or value.text is None:
        return ""
    if cell.get("t") == "s":
        return shared[int(value.text)]
    return value.text


def read_xlsx_rows(path: str | Path) -> list[dict[str, str]]:
    xlsx_path = Path(path)
    with zipfile.ZipFile(xlsx_path) as zf:
        shared = _shared_strings(zf)
        sheet_name = next(name for name in zf.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        root = ET.fromstring(zf.read(sheet_name))
        rows = root.findall(".//a:sheetData/a:row", NS)
        header = [_cell_value(cell, shared) for cell in rows[0].findall("a:c", NS)]
        records: list[dict[str, str]] = []
        for row in rows[1:]:
            values = [_cell_value(cell, shared) for cell in row.findall("a:c", NS)]
            values.extend([""] * (len(header) - len(values)))
            records.append(dict(zip(header, values)))
        return records


def parse_literal(value: str) -> Any:
    if value in ("", None):
        return []
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return []


class EscoMapper:
    def __init__(self, skills_path: str | Path, occupations_path: str | Path | None = None) -> None:
        self.skills_path = Path(skills_path)
        self.occupations_path = Path(occupations_path) if occupations_path else None
        self.skill_rows = read_xlsx_rows(self.skills_path)
        self.skill_labels = {row["conceptUri"]: row.get("preferredLabel", row["conceptUri"]) for row in self.skill_rows}
        self.skill_ancestors = {
            row["conceptUri"]: self._flatten_ancestors(row)
            for row in self.skill_rows
        }
        self.occupation_labels: dict[str, str] = {}
        if self.occupations_path and self.occupations_path.exists():
            occupation_rows = read_xlsx_rows(self.occupations_path)
            self.occupation_labels = {row["conceptUri"]: row.get("preferredLabel", row["conceptUri"]) for row in occupation_rows}

    def _flatten_ancestors(self, row: dict[str, str]) -> list[str]:
        ancestors: list[str] = []
        for column in ["skills_ancestors", "knowledge_ancestors", "traversal_ancestors", "language_ancestors"]:
            for path in parse_literal(row.get(column, "")):
                if isinstance(path, list):
                    ancestors.extend(str(item) for item in path)
        return list(dict.fromkeys(ancestors))

    def skill_label(self, uri: str) -> str:
        return self.skill_labels.get(uri, uri.rsplit("/", 1)[-1])

    def capability_family(self, uri: str) -> str:
        ancestors = self.skill_ancestors.get(uri) or []
        for ancestor in ancestors:
            if ancestor in self.skill_labels:
                return self.skill_labels[ancestor]
        return self.skill_label(uri)
