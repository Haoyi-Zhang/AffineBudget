#!/usr/bin/env python3
"""Offline, standard-library audit of bibliography identity and manuscript use.

The standalone repository audits the frozen scholarly/reference snapshots.  When the
artifact is inside the complete project, the same command additionally compares the
snapshots against the live manuscript bibliography and citation commands.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Set

ROOT = Path(__file__).resolve().parent
SCHOLARLY = ROOT / "scholarly"
EXPECTED_REFERENCES = 65
EXPECTED_CALIBRATION = {"same venue": 12, "influential": 5, "adjacent": 5}
EXPECTED_EXTERNAL_IDENTITIES = {
    "lowepower2020gem5": {
        "entry_type": "article", "year": "2020", "doi": "",
        "identifier": "arxiv:2007.03152", "primary_record": "https://www.gem5.org/publications/",
        "journal": "CoRR", "volume": "abs/2007.03152", "eprint": "2007.03152",
        "author_count": 78, "first_author": "Jason Lowe-Power", "last_author": "Éder F. Zulian",
    },
    "ubal2007multi2sim": {
        "entry_type": "inproceedings", "year": "2007", "doi": "10.1109/SBAC-PAD.2007.17",
        "identifier": "doi:10.1109/SBAC-PAD.2007.17", "primary_record": "https://doi.org/10.1109/SBAC-PAD.2007.17",
        "booktitle_contains": "SBAC-PAD", "pages": "62--68",
        "author_count": 4, "first_author": "Rafael Ubal", "last_author": "Pedro López",
    },
}


def parse_bib(path: Path) -> List[Dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    entries: List[Dict[str, str]] = []
    pos = 0
    while True:
        match = re.search(r"@(\w+)\s*\{\s*([^,]+),", text[pos:])
        if not match:
            break
        entry_type = match.group(1).lower()
        key = match.group(2).strip()
        cursor = pos + match.end()
        depth = 1
        end = cursor
        while end < len(text) and depth:
            if text[end] == "{":
                depth += 1
            elif text[end] == "}":
                depth -= 1
            end += 1
        if depth:
            raise ValueError(f"unterminated BibTeX entry: {key}")
        body = text[cursor : end - 1]

        def field(name: str) -> str:
            found = re.search(
                rf"(?is)(?:^|,)\s*{re.escape(name)}\s*=\s*"
                r"\{((?:[^{}]|\{[^{}]*\})*)\}",
                body,
            )
            return found.group(1).strip() if found else ""

        entries.append(
            {
                "bib_key": key,
                "entry_type": entry_type,
                "title": field("title"),
                "author": field("author"),
                "year": field("year"),
                "doi": field("doi"),
                "journal": field("journal"),
                "volume": field("volume"),
                "eprint": field("eprint"),
                "booktitle": field("booktitle"),
                "pages": field("pages"),
            }
        )
        pos = end
    return entries


def normalized_title(title: str) -> str:
    plain = re.sub(r"[{}\\]", "", title).lower()
    return re.sub(r"[^a-z0-9]+", "", plain)


def normalized_person(name: str) -> str:
    substitutions = {
        r"{\'E}": "É", r"{\'e}": "é", r"{\'o}": "ó", r"{\`a}": "à",
        r"{\"u}": "ü", r"{\"o}": "ö",
    }
    plain = name
    for source, target in substitutions.items():
        plain = plain.replace(source, target)
    plain = re.sub(r"[{}\\]", "", plain).lower()
    return re.sub(r"[^a-z0-9]+", "", plain)


def bib_authors(author_field: str) -> List[str]:
    return [part.strip() for part in author_field.split(" and ") if part.strip()]


def manuscript_citations(project_root: Path) -> Mapping[str, Set[str]]:
    paper = project_root / "paper"
    files = [paper / "main.tex", *sorted((paper / "sections").glob("*.tex"))]
    contexts: Dict[str, Set[str]] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\\cite[a-zA-Z*]*\s*\{([^}]*)\}", text):
            for key in match.group(1).split(","):
                contexts.setdefault(key.strip(), set()).add(path.stem)
    return contexts


def require(condition: bool, message: str, failures: List[str]) -> None:
    if not condition:
        failures.append(message)


def audit() -> Dict[str, object]:
    failures: List[str] = []
    bib_path = SCHOLARLY / "references.bib"
    entries = parse_bib(bib_path)
    keys = [row["bib_key"] for row in entries]
    require(len(entries) == EXPECTED_REFERENCES, f"expected {EXPECTED_REFERENCES} BibTeX entries, found {len(entries)}", failures)
    require(len(set(keys)) == len(keys), "duplicate BibTeX keys", failures)

    dois = [row["doi"].lower() for row in entries if row["doi"]]
    require(len(dois) == len(set(dois)), "duplicate DOI values", failures)
    titles = [normalized_title(row["title"]) for row in entries]
    require(all(titles), "empty normalized title", failures)
    require(len(titles) == len(set(titles)), "duplicate normalized titles", failures)
    require(all(re.fullmatch(r"(?:19|20)\d{2}", row["year"]) for row in entries), "invalid or missing publication year", failures)

    with (ROOT / "bibliography-audit.csv").open(newline="", encoding="utf-8") as handle:
        audit_rows = list(csv.DictReader(handle))
    audit_by_key = {row["bib_key"]: row for row in audit_rows}
    require(len(audit_rows) == EXPECTED_REFERENCES, f"expected {EXPECTED_REFERENCES} audit rows, found {len(audit_rows)}", failures)
    require(set(audit_by_key) == set(keys), "bibliography audit key coverage differs from BibTeX", failures)
    required_audit_fields = {
        "title",
        "year",
        "entry_type",
        "identifier",
        "primary_record",
        "record_type",
        "verification_scope",
        "metadata_status",
        "manuscript_contexts",
        "citation_status",
        "audit_note",
        "verified_on",
    }
    for entry in entries:
        row = audit_by_key.get(entry["bib_key"], {})
        missing = sorted(field for field in required_audit_fields if not row.get(field, "").strip())
        require(not missing, f"{entry['bib_key']}: empty audit fields {missing}", failures)
        require(row.get("metadata_status") in {"verified","externally-checked"}, f"{entry['bib_key']}: unsupported metadata status", failures)
        require(row.get("citation_status") == "cited-and-relevant", f"{entry['bib_key']}: citation relevance not accepted", failures)
        require(row.get("year") == entry["year"], f"{entry['bib_key']}: year differs between audit and BibTeX", failures)
        require(row.get("entry_type") == entry["entry_type"], f"{entry['bib_key']}: entry type differs between audit and BibTeX", failures)
        require(normalized_title(row.get("title", "")) == normalized_title(entry["title"]), f"{entry['bib_key']}: title differs between audit and BibTeX", failures)
        require(row.get("primary_record", "").startswith("https://"), f"{entry['bib_key']}: primary record is not HTTPS", failures)
        if entry["doi"]:
            expected_identifier = "doi:" + entry["doi"]
            expected_record = "https://doi.org/" + entry["doi"]
            require(row.get("identifier", "").lower() == expected_identifier.lower(), f"{entry['bib_key']}: DOI identifier mismatch", failures)
            require(row.get("primary_record", "").lower() == expected_record.lower(), f"{entry['bib_key']}: DOI record mismatch", failures)

    identity_path = ROOT / "results" / "bibliographic-identity-check.json"
    identity_data = json.loads(identity_path.read_text(encoding="utf-8"))
    identity_rows = {row["bib_key"]: row for row in identity_data.get("records", [])}
    require(set(identity_rows) == set(EXPECTED_EXTERNAL_IDENTITIES), "external identity receipt key coverage differs", failures)
    by_key = {entry["bib_key"]: entry for entry in entries}
    for key, expected in EXPECTED_EXTERNAL_IDENTITIES.items():
        entry = by_key[key]; row = audit_by_key[key]; identity = identity_rows.get(key, {})
        require(entry["entry_type"] == expected["entry_type"], f"{key}: corrected entry type mismatch", failures)
        require(entry["year"] == expected["year"], f"{key}: corrected year mismatch", failures)
        require(entry["doi"].lower() == expected["doi"].lower(), f"{key}: corrected DOI mismatch", failures)
        require(row.get("identifier", "").lower() == expected["identifier"].lower(), f"{key}: external identifier mismatch", failures)
        require(row.get("primary_record", "").lower() == expected["primary_record"].lower(), f"{key}: external primary record mismatch", failures)
        require(row.get("metadata_status") == "externally-checked", f"{key}: external check status missing", failures)
        require(identity.get("entry_type") == expected["entry_type"] and identity.get("year") == expected["year"], f"{key}: external identity receipt differs", failures)
        require(identity.get("identifier", "").lower() == expected["identifier"].lower(), f"{key}: external identity receipt identifier differs", failures)
        authors = bib_authors(entry.get("author", ""))
        require(len(authors) == expected["author_count"], f"{key}: corrected author count mismatch", failures)
        if authors:
            require(normalized_person(authors[0]) == normalized_person(expected["first_author"]), f"{key}: corrected first author mismatch", failures)
            require(normalized_person(authors[-1]) == normalized_person(expected["last_author"]), f"{key}: corrected last author mismatch", failures)
        require(identity.get("author_count") == expected["author_count"], f"{key}: external receipt author count differs", failures)
        require(normalized_person(identity.get("first_author", "")) == normalized_person(expected["first_author"]), f"{key}: external receipt first author differs", failures)
        require(normalized_person(identity.get("last_author", "")) == normalized_person(expected["last_author"]), f"{key}: external receipt last author differs", failures)
        if key == "lowepower2020gem5":
            require(entry.get("journal") == expected["journal"], f"{key}: corrected journal mismatch", failures)
            require(entry.get("volume") == expected["volume"], f"{key}: corrected volume mismatch", failures)
            require(entry.get("eprint") == expected["eprint"], f"{key}: corrected arXiv identifier mismatch", failures)
            require("others" not in entry.get("author", "").lower(), f"{key}: truncated author list", failures)
        if key == "ubal2007multi2sim":
            require(expected["booktitle_contains"] in entry.get("booktitle", ""), f"{key}: corrected venue mismatch", failures)
            require("ISPASS" not in entry.get("booktitle", "").upper(), f"{key}: stale ISPASS venue remains", failures)
            require(entry.get("pages") == expected["pages"], f"{key}: corrected pages mismatch", failures)

    with (SCHOLARLY / "citation-usage.csv").open(newline="", encoding="utf-8") as handle:
        usage_rows = list(csv.DictReader(handle))
    usage = {row["bib_key"]: row["manuscript_contexts"] for row in usage_rows}
    require(len(usage_rows) == EXPECTED_REFERENCES, f"expected {EXPECTED_REFERENCES} citation-usage rows, found {len(usage_rows)}", failures)
    require(set(usage) == set(keys), "citation-usage key coverage differs from BibTeX", failures)
    for key in keys:
        require(bool(usage.get(key, "").strip()), f"{key}: no manuscript citation context", failures)
        require(usage.get(key, "") == audit_by_key.get(key, {}).get("manuscript_contexts", ""), f"{key}: citation contexts differ between audit files", failures)

    with (ROOT / "literature-calibration.csv").open(newline="", encoding="utf-8") as handle:
        calibration = list(csv.DictReader(handle))
    group_counts = Counter(row["group"] for row in calibration)
    require(dict(group_counts) == EXPECTED_CALIBRATION, f"literature calibration counts differ: {dict(group_counts)}", failures)
    calibration_keys = [row["bib_key"] for row in calibration]
    require(len(calibration_keys) == len(set(calibration_keys)) == sum(EXPECTED_CALIBRATION.values()), "literature calibration keys are missing or duplicated", failures)
    require(set(calibration_keys) <= set(keys), "literature calibration contains an unknown BibTeX key", failures)
    for row in calibration:
        missing = [name for name, value in row.items() if not value.strip()]
        require(not missing, f"{row.get('bib_key','?')}: empty literature-calibration fields {missing}", failures)
        require(row["url"].startswith("https://"), f"{row['bib_key']}: calibration URL is not HTTPS", failures)

    # Inside the complete project, prove that the standalone snapshots still match
    # the actual manuscript rather than merely agreeing with one another.
    project_root = ROOT.parent
    paper_bib = project_root / "paper" / "references.bib"
    live_manuscript_checked = paper_bib.exists()
    if live_manuscript_checked:
        require(paper_bib.read_bytes() == bib_path.read_bytes(), "paper/references.bib differs from artifact scholarly snapshot", failures)
        live = manuscript_citations(project_root)
        require(set(live) == set(keys), "live manuscript citation keys differ from bibliography", failures)
        for key in keys:
            require(";".join(sorted(live.get(key, set()))) == usage[key], f"{key}: live manuscript contexts differ from citation snapshot", failures)

    report: Dict[str, object] = {
        "references": len(entries),
        "doi_records": len(dois),
        "official_non_doi_records": len(entries) - len(dois),
        "externally_rechecked_records": len(EXPECTED_EXTERNAL_IDENTITIES),
        "external_identity_live_query": False,
        "cited_references": sum(bool(usage.get(key, "").strip()) for key in keys),
        "unused_references": sorted(set(keys) - set(usage)),
        "calibration_rows": len(calibration),
        "calibration_groups": dict(group_counts),
        "live_manuscript_checked": live_manuscript_checked,
        "failures": failures,
        "status": "pass" if not failures else "fail",
    }
    return report


def main() -> int:
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
