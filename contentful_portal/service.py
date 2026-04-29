"""
Build the same table rows as scripts/contentful_entries_readable_csv.py from a bundle.
"""
import csv
import importlib.util
import re
import sys
from io import StringIO
from pathlib import Path
from types import ModuleType
from typing import List, Optional, Set, Tuple

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = _ROOT / "scripts" / "contentful_entries_readable_csv.py"


def load_csv_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ce_csv", _SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError("Cannot load contentful_entries_readable_csv")
    m = importlib.util.module_from_spec(spec)
    sys.modules["ce_csv"] = m
    spec.loader.exec_module(m)  # type: ignore[union-attr]
    return m


def build_rows_from_bundle(
    bundle: dict, m: Optional[ModuleType] = None
) -> Tuple[List[dict], List[str], List[str]]:
    m = m or load_csv_module()
    entry_map, asset_map, ct_map = m.build_maps(bundle)
    from_bundle: List[str] = []
    for loco in bundle.get("locales", []):
        c = loco.get("code")
        if c and c not in from_bundle:
            from_bundle.append(c)
    if not from_bundle:
        from_bundle = ["en-US", "ar"]
    ordered: List[str] = []
    for c in ("en-US", "ar", "en"):
        if c in from_bundle and c not in ordered:
            ordered.append(c)
    for c in from_bundle:
        if c not in ordered:
            ordered.append(c)
    cols = [
        "entry_id",
        "content_type",
        "content_type_name",
        "title_lookup",
        "created_at",
        "updated_at",
    ] + [
        h
        for c in ordered
        for h in (f"fields_list_{c}", f"all_fields_{c}")
    ] + ["all_links_deduped"]
    rows2: List[dict] = []
    for e in bundle.get("entries", []):
        eid = (e.get("sys", {}) or {}).get("id")
        ctid = m.entry_type_id(e)
        ct = ct_map.get(ctid) or {}
        ctn = ct.get("name") or ctid
        sys_ = e.get("sys", {}) or {}
        row2 = {
            "entry_id": eid,
            "content_type": ctid,
            "content_type_name": ctn,
            "title_lookup": m.best_title(e),
            "created_at": sys_.get("createdAt", ""),
            "updated_at": sys_.get("updatedAt", ""),
        }
        master: Set[str] = set()
        for loc in ordered:
            l2: Set[str] = set()
            body, fl = m.build_locale_text(
                e, ct, loc, entry_map, asset_map, l2
            )
            row2[f"fields_list_{loc}"] = fl
            row2[f"all_fields_{loc}"] = body
            master |= l2
        m.collect_symbol_links(e.get("fields"), master)
        tcomb = " ".join((row2.get(f"all_fields_{c}", "") for c in ordered))
        for u in re.findall(r"https?://[^\s)'\]\"<>]+", tcomb or ""):
            master.add(u)
        row2["all_links_deduped"] = "\n".join(sorted(master))
        for c in cols:
            if c not in row2:
                row2[c] = ""
        rows2.append(row2)
    return rows2, cols, ordered


def render_csv_string(rows: List[dict], cols: List[str]) -> str:
    out = StringIO()
    w = csv.DictWriter(
        out, fieldnames=cols, extrasaction="ignore", quoting=csv.QUOTE_MINIMAL
    )
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return out.getvalue()
