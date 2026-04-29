#!/usr/bin/env python3
"""
Human-readable entries CSV (titles, text, links — no raw JSON) from
contentful-export/space_export.json -> contentful-export/entries_readable.csv
"""
import csv
import json
import os
import re
import sys
from html import unescape
from io import StringIO
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
JSON_IN = os.path.join(ROOT, "contentful-export", "space_export.json")
OUT_CSV = os.path.join(ROOT, "contentful-export", "entries_readable.csv")

LOCALE_ORDER = ("en-US", "ar", "en")

# --- index helpers ---


def build_maps(bundle) -> Tuple[dict, dict, dict]:
    entry_map = {e["sys"]["id"]: e for e in bundle.get("entries", []) if e.get("sys")}
    asset_map = {a["sys"]["id"]: a for a in bundle.get("assets", []) if a.get("sys")}
    ct_map = {c["sys"]["id"]: c for c in bundle.get("contentTypes", []) if c.get("sys")}
    return entry_map, asset_map, ct_map


def asset_file_url(a: dict, loc: Optional[str] = None) -> str:
    f = (a.get("fields") or {}).get("file") or {}
    if not f:
        return ""
    if loc and loc in f and isinstance(f[loc], dict) and f[loc].get("url"):
        u = f[loc]["url"]
    else:
        u = ""
        for v in f.values():
            if isinstance(v, dict) and v.get("url"):
                u = v["url"]
                break
    if u and u.startswith("//"):
        u = "https:" + u
    return u or ""


def asset_label(a: dict) -> str:
    t = (a.get("fields") or {}).get("title") or {}
    title = " ".join(str(x) for x in t.values() if x) if isinstance(t, dict) else str(t)
    u = asset_file_url(a)
    if title and u:
        return f"{title}  ({u})"
    return title or u or a.get("sys", {}).get("id", "")


def best_title(e: dict) -> str:
    f = e.get("fields") or {}
    for key in ("title", "privateTitle", "name", "label", "description"):
        fld = f.get(key)
        if not isinstance(fld, dict):
            continue
        for loc in LOCALE_ORDER:
            v = fld.get(loc)
            if v and str(v).strip():
                return str(v).strip()
        for v in fld.values():
            if v and isinstance(v, str) and v.strip():
                return v.strip()
    return (e.get("sys") or {}).get("id", "")


def best_slug(e: dict) -> str:
    slug = (e.get("fields") or {}).get("slug")
    if not isinstance(slug, dict):
        return ""
    for loc in LOCALE_ORDER:
        if slug.get(loc):
            return str(slug[loc])
    for v in slug.values():
        if v:
            return str(v)
    return ""


def entry_type_id(e: dict) -> str:
    return (e.get("sys") or {}).get("contentType", {}).get("sys", {}).get("id", "")


def label_entry(
    eid: str, entries: dict, assets: dict, stack: Optional[Set[str]] = None
) -> str:
    if stack is None:
        stack = set()
    if eid in stack or len(stack) > 5:
        return f"[circular: {eid}]"
    e = entries.get(eid)
    if not e:
        return f"[missing entry {eid}]"
    t = entry_type_id(e)
    if t == "article":
        ttl, sl = best_title(e), best_slug(e)
        if ttl and sl:
            return f"{ttl}  (/{sl})"
        return ttl or eid
    return f"{t.replace('_', ' ')}: {best_title(e) or eid}"


def _inline(
    node: dict,
    entries: dict,
    assets: dict,
    links: Set[str],
    stack: Set[str],
) -> str:
    parts = []
    for ch in node.get("content") or []:
        parts.append(richtext_node(ch, entries, assets, links, stack))
    if node.get("nodeType", "").startswith("paragraph") or node.get("nodeType") in (
        "list-item",
        "heading-1",
        "heading-2",
        "heading-3",
        "heading-4",
        "heading-5",
        "heading-6",
    ):
        return "".join(parts)
    return " ".join(parts) if node.get("nodeType") in ("list-item",) else "".join(
        parts
    )


def richtext_node(
    node: Any,
    entries: dict,
    assets: dict,
    links: Set[str],
    stack: Set[str],
) -> str:
    if not isinstance(node, dict):
        return str(node) if node is not None else ""

    nt = node.get("nodeType", "")

    if nt == "text":
        t = (node or {}).get("value") or ""
        marks = {m.get("type") for m in (node.get("marks") or []) if isinstance(m, dict)}
        if "bold" in marks and "italic" in marks:
            return f"**_{t}_**"
        if "bold" in marks:
            return f"**{t}**"
        if "italic" in marks or "em" in marks or "italics" in marks:
            return f"_{t}_"
        return t

    if nt == "paragraph":
        t = _inline(node, entries, assets, links, stack)
        return t.strip() if t else ""

    for hn in (
        "heading-1",
        "heading-2",
        "heading-3",
        "heading-4",
        "heading-5",
        "heading-6",
    ):
        if nt == hn:
            lvl = min(int(hn.split("-")[-1]), 3)
            t = _inline(node, entries, assets, links, stack)
            return f"\n{('#' * lvl)} {t}\n" if t else f"\n{('#' * lvl)} \n"

    if nt in ("ordered-list", "unordered-list"):
        buf = StringIO()
        ordered = nt == "ordered-list"
        n = 0
        for c in node.get("content") or []:
            if c.get("nodeType") != "list-item":
                continue
            n += 1
            t = richtext_node(c, entries, assets, links, stack)
            prefix = f"{n}. " if ordered else "• "
            buf.write(prefix + t.replace("\n\n", "\n").strip() + "\n")
        return "\n" + buf.getvalue().rstrip() + "\n\n"

    if nt == "list-item":
        return _inline(node, entries, assets, links, stack)

    if nt == "table":
        lines = []
        for row in node.get("content") or []:
            if row.get("nodeType") != "table-row":
                continue
            row_cells = []
            for c in row.get("content") or []:
                if c.get("nodeType") == "table-cell":
                    t = richtext_node(c, entries, assets, links, stack)
                    row_cells.append(t.replace("\n", " ").replace("|", "/").strip())
            if row_cells:
                lines.append("  |  ".join(row_cells))
        return "\n" + "\n".join(lines) + "\n\n" if lines else ""

    if nt in ("table-row", "table-cell"):
        return _inline(node, entries, assets, links, stack).strip() or " ".join(
            richtext_node(ch, entries, assets, links, stack) for ch in (node.get("content") or [])
        )

    if nt == "hyperlink":
        data = (node.get("data") or {})
        uri = data.get("uri") or ""
        if uri:
            links.add(uri)
        inner = _inline(node, entries, assets, links, stack)
        if inner and uri:
            return f"{inner}  →  {uri}"
        return inner or (uri or "")

    if nt in ("entry-hyperlink", "embedded-entry-block", "embedded-entry-inline"):
        d = (node.get("data") or {})
        tgt = d.get("target") or {}
        eid = (tgt or {}).get("sys", {}).get("id")
        if eid:
            stack2 = set(stack) | {eid}
            lbl = label_entry(eid, entries, assets, stack2)
            if node.get("content"):
                return _inline(node, entries, assets, links, stack)
            return f"«{lbl}»"
        if node.get("content"):
            return _inline(node, entries, assets, links, stack)
        return "«entry»"

    if nt == "embedded-asset-block":
        d = (node.get("data") or {})
        tgt = d.get("target") or {}
        aid = (tgt or {}).get("sys", {}).get("id")
        a = assets.get(aid) if aid else None
        if a:
            u = asset_file_url(a)
            if u:
                links.add(u)
            return f"[Media: {asset_label(a)}]"
        return f"[Media: {aid}]" if aid else "[Media]"

    if nt == "hr" or nt == "horizontal-rule":
        return "\n" + "—" * 40 + "\n"

    if nt == "document" or (not nt and (node.get("content") is not None)):
        blocks = [
            richtext_node(c, entries, assets, links, stack)
            for c in (node.get("content") or [])
        ]
        return "\n\n".join(b for b in blocks if (b is not None and str(b).strip() != ""))

    if node.get("content") is not None:
        return _inline(node, entries, assets, links, stack)
    return ""


def richtext_to_text(doc: dict, entries: dict, assets: dict) -> Tuple[str, List[str]]:
    if not doc or not isinstance(doc, dict):
        return ("", [])
    links: Set[str] = set()
    text = richtext_node(doc, entries, assets, links, set()).strip()
    return (text, sorted(links))


def is_urlish(s: str) -> bool:
    s = (s or "").strip()
    return s.startswith("http://") or s.startswith("https://") or s.startswith("www.")


_LOOKS_HTML = re.compile(r"<\s*[a-zA-Z][\s\w:=-]*[^>]*>")


def looks_like_html(s: str) -> bool:
    if not s or not isinstance(s, str) or len(s) < 7:
        return False
    return _LOOKS_HTML.search(s) is not None


def _html_fallback_strip(raw: str, links_out: Set[str]) -> str:
    for m in re.findall(r'(?i)href\s*=\s*["\']?([^"\'\s>]+)', raw):
        if m and not m.startswith("#"):
            links_out.add(m.strip().rstrip("&"))
    t = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    t = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", t)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|h[1-6]|tr|li)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def html_to_readable(raw: str, links_out: Set[str]) -> str:
    """
    Turn HTML (as stored in some Text / Symbol fields) into UI-like plain text
    and collect hrefs into links_out.
    """
    if not raw or not looks_like_html(raw):
        return raw.strip() if isinstance(raw, str) else str(raw)
    if BeautifulSoup is not None:
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript", "head", "meta", "link"]):
            tag.decompose()
        for a in soup.find_all("a", href=True):
            h = (a.get("href") or "").strip()
            if h and not h.startswith("#"):
                links_out.add(h)
        for im in soup.find_all("img", src=True):
            s = (im.get("src") or "").strip()
            if s:
                if s.startswith("//"):
                    s = "https:" + s
                links_out.add(s)
        for br in soup.find_all("br"):
            br.replace_with("\n")
        for hr in soup.find_all("hr"):
            hr.replace_with("\n" + "—" * 20 + "\n")
        text = soup.get_text(separator="\n", strip=True)
        text = unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    return _html_fallback_strip(raw, links_out)


def maybe_richtext_json_string(value: str, entry_map, asset_map, links_all) -> Optional[str]:
    """If a Text field accidentally holds stringified richtext JSON, convert it."""
    s = (value or "").lstrip()
    if not s.startswith("{"):
        return None
    if '"nodeType"' not in s:
        return None
    try:
        doc = json.loads(s)
    except json.JSONDecodeError:
        return None
    if not isinstance(doc, dict) or doc.get("nodeType") not in (None, "document"):
        return None
    txt, uris = richtext_to_text(doc, entry_map, asset_map)
    links_all.update(uris)
    return txt


# --- per-field format ---


def format_value(
    field: dict,
    value: Any,
    loc: str,
    entry_map: dict,
    asset_map: dict,
    links_all: Set[str],
) -> str:
    t = (field or {}).get("type")
    lid = (field or {}).get("id", "")

    if value is None:
        return ""

    if t == "RichText":
        if not isinstance(value, dict):
            return str(value)
        txt, uris = richtext_to_text(value, entry_map, asset_map)
        links_all.update(uris)
        return txt

    if t in ("Text", "Symbol", "Date"):
        if t == "Date":
            return str(value) if not isinstance(value, (dict, list)) else str(value)
        raw = str(value) if not isinstance(value, (dict, list)) else str(value)
        rt = maybe_richtext_json_string(raw, entry_map, asset_map, links_all)
        if rt is not None:
            return rt
        if looks_like_html(raw):
            return html_to_readable(raw, links_all)
        return raw

    if t in ("Number", "Integer") or t == "Number":
        return str(value)

    if t == "Boolean":
        return "Yes" if value else "No"

    if t == "Object" and isinstance(value, dict):
        if not value:
            return ""
        return "\n".join(f"  {k}: {v!s}" for k, v in value.items())

    if t == "Link":
        ltype = (field or {}).get("linkType", "")
        link = value if isinstance(value, dict) else None
        if ltype == "Entry":
            eid = (link or {}).get("sys", {}).get("id")
            return label_entry(eid, entry_map, asset_map) if eid else ""
        if ltype == "Asset":
            aid = (link or {}).get("sys", {}).get("id")
            a = asset_map.get(aid) if aid else None
            return asset_label(a) if a else f"[asset {aid}]" if aid else ""
        return ""

    if t == "Array":
        if not value:
            return ""
        if isinstance(value, list) and value and not isinstance(
            (value[0] if value else None), dict
        ):
            return "  •  " + "\n  •  ".join(str(x) for x in value)
        if isinstance(value, list):
            ltype = (field or {}).get("items", {}).get("linkType", "")
            parts = []
            for item in value:
                if not isinstance(item, dict) or (item or {}).get("sys", {}).get("type") != "Link":
                    parts.append(str(item))
                    if is_urlish(str(item)):
                        links_all.add(str(item).strip())
                    continue
                lt = (item.get("sys") or {}).get("linkType", "")
                iid = (item.get("sys") or {}).get("id", "")
                if ltype == "Entry" and lt == "Entry":
                    parts.append(f"•  {label_entry(iid, entry_map, asset_map)}")
                elif ltype == "Asset" and lt == "Asset":
                    a = asset_map.get(iid)
                    parts.append("•  " + (asset_label(a) if a else f"asset {iid}"))
                else:
                    parts.append(f"•  {iid} ({lt})")
            return "\n".join(parts)
        return str(value)

    if (
        isinstance(value, dict)
        and t not in ("Object", "RichText")
        and not t == "Array"
    ):
        v2 = value.get(loc)
        if v2 is not None and t in ("Text", "Symbol", "Text"):
            return str(v2)
    return str(value) if not isinstance(value, dict) else ""


def get_localized(
    field_def: dict, fields: dict, fid: str, loc: str, default_loc: str
) -> Any:
    v = (fields or {}).get(fid)
    if not isinstance(v, dict):
        return v
    if field_def.get("localized"):
        if v.get(loc) is not None:
            return v.get(loc)
        return None
    else:
        # Not localized: CMA still nests under a locale; show only in that column
        if "en-US" in v and v.get("en-US") is not None:
            return v.get("en-US") if loc == "en-US" else None
        if "ar" in v and v.get("ar") is not None:
            return v.get("ar") if loc == "ar" else None
        if len(v) == 1:
            (only_k, only_v) = next(iter(v.items()))
            return only_v if loc == only_k else None
        if v.get(loc) is not None:
            return v.get(loc)
        for l in (loc, "en-US", "ar", default_loc):
            if l and v.get(l) is not None:
                return v.get(l) if l == loc else None
    return None


def _format_loose_value(
    v: Any, entry_map: dict, asset_map: dict, links: Set[str]
) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        rt = maybe_richtext_json_string(v, entry_map, asset_map, links)
        if rt is not None:
            return rt
        if looks_like_html(v):
            return html_to_readable(v, links)
        return v
    return str(v)


def build_locale_text(
    entry: dict,
    ct: dict,
    loc: str,
    entry_map: dict,
    asset_map: dict,
    all_links: Set[str],
) -> Tuple[str, str]:
    """
    (formatted_body, comma_separated_field_names) for this locale.
    """
    fields = entry.get("fields") or {}
    fdefs = (ct or {}).get("fields", [])
    name_by_id = {f.get("id"): f.get("name", f.get("id")) for f in fdefs}
    blocks: List[Tuple[str, str]] = []

    for fdef in fdefs:
        fid = fdef.get("id", "")
        label = (fdef.get("name") or fid).strip()
        v = get_localized(fdef, fields, fid, loc, "en-US")
        if v is None or (
            isinstance(v, (str, list, dict)) and (not v or (isinstance(v, dict) and v == {}))
        ):
            continue
        s = format_value(fdef, v, loc, entry_map, asset_map, all_links)
        s = s.strip() if isinstance(s, str) else s
        if s is None or s == "":
            if fdef.get("type") == "Boolean" and v is False:
                s = "No"
            else:
                continue
        if isinstance(s, str) and s == "No" and fdef.get("type") == "Boolean" and v is False:
            blocks.append((label, "No"))
            continue
        blocks.append((label, str(s) if not isinstance(s, (str, int, float, bool)) else s))

    for fid, raw in fields.items():
        if any(fd.get("id") == fid for fd in fdefs) or not isinstance(raw, dict):
            continue
        v = raw.get(loc)
        if v is None or (isinstance(v, (dict, list)) and not v):
            continue
        s = _format_loose_value(v, entry_map, asset_map, all_links)
        if s and s.strip():
            label = (name_by_id.get(fid) or fid) + " (extra)"
            blocks.append((label, s.strip()))

    if not blocks:
        return ("", "")

    names = [b[0] for b in blocks]
    list_line = "FIELDS: " + ", ".join(names)
    parts: List[str] = [list_line, ""]
    for i, (label, value) in enumerate(blocks, 1):
        val = value if isinstance(value, str) else str(value)
        parts.append("---")
        parts.append(f"{i}. {label}")
        parts.append(val)
    body = "\n\n".join(parts)
    return (body.strip(), ", ".join(names))


def collect_symbol_links(
    value: Any, out: Set[str]
) -> None:
    if isinstance(value, str) and is_urlish(value):
        out.add(value.strip())
    elif isinstance(value, dict):
        for v in value.values():
            collect_symbol_links(v, out)
    elif isinstance(value, list):
        for v in value:
            collect_symbol_links(v, out)


def main() -> None:
    if not os.path.isfile(JSON_IN):
        print("Missing", JSON_IN, "— run contentful_mapi_export.py first", file=sys.stderr)
        sys.exit(1)
    with open(JSON_IN, "r", encoding="utf-8") as f:
        bundle = json.load(f)
    entry_map, asset_map, ct_map = build_maps(bundle)
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
        ctid = entry_type_id(e)
        ct = ct_map.get(ctid) or {}
        ctn = ct.get("name") or ctid
        sys_ = e.get("sys", {}) or {}
        row2 = {
            "entry_id": eid,
            "content_type": ctid,
            "content_type_name": ctn,
            "title_lookup": best_title(e),
            "created_at": sys_.get("createdAt", ""),
            "updated_at": sys_.get("updatedAt", ""),
        }
        master: Set[str] = set()
        for loc in ordered:
            l2: Set[str] = set()
            body, fl = build_locale_text(
                e, ct, loc, entry_map, asset_map, l2
            )
            row2[f"fields_list_{loc}"] = fl
            row2[f"all_fields_{loc}"] = body
            master |= l2
        collect_symbol_links(e.get("fields"), master)
        tcomb = " ".join((row2.get(f"all_fields_{c}", "") for c in ordered))
        for u in re.findall(r"https?://[^\s)'\]\"<>]+", tcomb or ""):
            master.add(u)
        row2["all_links_deduped"] = "\n".join(sorted(master))
        for c in cols:
            if c not in row2:
                row2[c] = ""
        rows2.append(row2)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w2 = csv.DictWriter(
            f, fieldnames=cols, extrasaction="ignore", quoting=csv.QUOTE_MINIMAL
        )
        w2.writeheader()
        for r in rows2:
            w2.writerow(r)
    print(
        json.dumps(
            {
                "wrote": OUT_CSV,
                "rows": len(rows2),
                "locales": ordered,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
