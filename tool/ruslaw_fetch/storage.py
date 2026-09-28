"""Resumable, idempotent on-disk storage: one JSON + one Markdown per act, plus a manifest.json
that tracks what's already been fetched (by hash + redid) so re-runs skip unchanged documents —
this is what makes `ruslaw-fetch update` cheap and polite to the source server.
"""
import json
import os
import re
import time

MANIFEST_NAME = "manifest.json"


def slugify(name, number=""):
    base = f"{number}_{name}" if number else name
    base = re.sub(r"[^\w\-]+", "_", base, flags=re.UNICODE).strip("_")
    return base[:120]


def load_manifest(out_dir):
    path = os.path.join(out_dir, MANIFEST_NAME)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(out_dir, manifest):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, MANIFEST_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)


def already_current(manifest, hash_, redid):
    entry = manifest.get(hash_)
    return bool(entry and entry.get("redid") == redid)


def write_act(out_dir, *, category, hash_, number, name, docstate, red, articles, source_url):
    """category: 'codes' or 'laws'. Writes <slug>.json (full structured record) and
    <slug>.md (human-readable, article headings) under out_dir/<category>/. Returns the slug."""
    slug = slugify(name, number)
    cat_dir = os.path.join(out_dir, category)
    os.makedirs(cat_dir, exist_ok=True)

    reddate = red["reddate"] if red else ""
    date_valid = f"{reddate[:4]}-{reddate[4:6]}-{reddate[6:8]}" if reddate else ""

    record = {
        "slug": slug,
        "number": number,
        "name": name,
        "docstate": docstate,
        "redaction_date": date_valid,
        "redid": red["redid"] if red else None,
        "hash": hash_,
        "source_url": source_url,
        "license": "official text of a legal act, not copyrightable under Russian Civil Code Art. 1259(6)",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_articles": len(articles),
        "articles": articles,
    }
    with open(os.path.join(cat_dir, slug + ".json"), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    md_lines = [f"# {name}", "", f"- Номер: {number or '—'}", f"- Состояние: {docstate}",
                f"- Актуальная редакция на: {date_valid}", f"- Источник: {source_url}", ""]
    for a in articles:
        heading = f"## Статья {a['number']}" if a["number"] else f"## {a['title']}"
        if a["number"] and a["title"]:
            heading += f". {a['title']}"
        md_lines.append(heading)
        md_lines.append("")
        md_lines.append(a["text"])
        md_lines.append("")
    with open(os.path.join(cat_dir, slug + ".md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return slug


def write_jsonl_index(out_dir, category):
    """Rebuilds <category>.jsonl (one line per article, across all acts in that category) —
    the flat, RAG-friendly format."""
    cat_dir = os.path.join(out_dir, category)
    out_path = os.path.join(out_dir, f"{category}.jsonl")
    n = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for fn in sorted(os.listdir(cat_dir)) if os.path.isdir(cat_dir) else []:
            if not fn.endswith(".json") or fn == MANIFEST_NAME:
                continue
            with open(os.path.join(cat_dir, fn), encoding="utf-8") as f:
                rec = json.load(f)
            for a in rec["articles"]:
                row = {
                    "act_slug": rec["slug"], "act_name": rec["name"], "act_number": rec["number"],
                    "redaction_date": rec["redaction_date"], "source_url": rec["source_url"],
                    "article_number": a["number"], "article_title": a["title"], "text": a["text"],
                }
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1
    return out_path, n
