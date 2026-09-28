#!/usr/bin/env python3
"""ruslaw-fetch CLI.

Examples:
    ruslaw-fetch codes                        # fetch/update all 24 RF codes (data/codes/)
    ruslaw-fetch codes --only nk_ch1,koap      # just a subset (by registry key)
    ruslaw-fetch laws                          # fetch/update the curated federal-laws list
    ruslaw-fetch law --number 400-ФЗ --name "страховых пенсиях"   # fetch one specific law
    ruslaw-fetch update --since 2026-09-01     # discover + refresh anything published since date
    ruslaw-fetch list-codes                    # print the codes registry
"""
import argparse
import json
import os
import sys

from .actual_pravo import ActualPravoClient
from .publication_pravo import PublicationPravoClient
from .articles import html_to_text, split_articles
from .storage import load_manifest, save_manifest, already_current, write_act, write_jsonl_index

HERE = os.path.dirname(os.path.abspath(__file__))


def load_registry(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def fetch_document(client, out_dir, *, category, hash_, number, name, manifest, force=False):
    card, red, redtext = client.get_actual_redaction(hash_)
    if not redtext:
        print(f"  SKIP (no text): {name} [{number}]")
        return None
    if not force and red and already_current(manifest, hash_, red["redid"]):
        print(f"  up to date: {name} [{number}] (redaction {red['reddate']})")
        return manifest[hash_]["slug"]
    text = html_to_text(redtext)
    articles = split_articles(text)
    url = f"http://actual.pravo.gov.ru/content/content.html#hash={hash_}&ttl=1"
    slug = write_act(out_dir, category=category, hash_=hash_, number=number,
                      name=card.get("docname") or name, docstate=card.get("docstate", ""),
                      red=red, articles=articles, source_url=url)
    manifest[hash_] = {"slug": slug, "redid": red["redid"] if red else None,
                        "redaction_date": (red["reddate"] if red else ""), "number": number}
    print(f"  OK: {name} [{number}] -> {slug} ({len(articles)} articles)")
    return slug


def cmd_codes(args):
    client = ActualPravoClient()
    codes = load_registry("codes_registry.json")
    only = set(args.only.split(",")) if args.only else None
    manifest = load_manifest(os.path.join(args.out, "codes"))
    for i, c in enumerate(codes):
        key = c.get("key") or c["number"]
        if only and key not in only and c["number"] not in only:
            continue
        fetch_document(client, args.out, category="codes", hash_=c["hash"], number=c["number"],
                        name=c["name"], manifest=manifest, force=args.force)
        save_manifest(os.path.join(args.out, "codes"), manifest)
    path, n = write_jsonl_index(args.out, "codes")
    print(f"Wrote {path} ({n} article rows)")


def cmd_laws(args):
    client = ActualPravoClient()
    laws = load_registry("laws_registry.json")
    only = set(args.only.split(",")) if args.only else None
    manifest = load_manifest(os.path.join(args.out, "laws"))
    for entry in laws:
        key = entry.get("key") or entry["number"]
        if only and key not in only:
            continue
        found = client.find_hash(entry["number"], entry["name_substr"])
        if not found:
            print(f"  NOT FOUND: {entry['number']} / {entry['name_substr']}")
            continue
        hash_, title = found
        fetch_document(client, args.out, category="laws", hash_=hash_, number=entry["number"],
                        name=entry.get("name", title), manifest=manifest, force=args.force)
        save_manifest(os.path.join(args.out, "laws"), manifest)
    path, n = write_jsonl_index(args.out, "laws")
    print(f"Wrote {path} ({n} article rows)")


def cmd_law(args):
    client = ActualPravoClient()
    found = client.find_hash(args.number, args.name)
    if not found:
        print("NOT FOUND"); sys.exit(1)
    hash_, title = found
    manifest = load_manifest(os.path.join(args.out, "laws"))
    fetch_document(client, args.out, category="laws", hash_=hash_, number=args.number,
                    name=title, manifest=manifest, force=args.force)
    save_manifest(os.path.join(args.out, "laws"), manifest)


def cmd_update(args):
    """Discover newly published federal laws since a date (via publication.pravo.gov.ru metadata)
    and fetch/refresh any that match our curated topics-of-interest keyword list; also always
    re-checks every act already in the manifest in case its redaction changed."""
    pub = PublicationPravoClient()
    client = ActualPravoClient()
    items = pub.new_federal_laws_since(args.since)
    print(f"{len(items)} federal laws published since {args.since}")
    laws = load_registry("laws_registry.json")
    keywords = set()
    for l in laws:
        keywords.update(l["name_substr"].lower().split())
    manifest = load_manifest(os.path.join(args.out, "laws"))
    for it in items:
        name = (it.get("name") or "").lower()
        if not any(k in name for k in keywords):
            continue
        number = it.get("number", "")
        found = client.find_hash(number, it.get("name", "")[:40])
        if not found:
            continue
        hash_, title = found
        fetch_document(client, args.out, category="laws", hash_=hash_, number=number,
                        name=title, manifest=manifest)
        save_manifest(os.path.join(args.out, "laws"), manifest)
    # also refresh everything we already track, in case its redaction moved on
    for hash_, entry in list(manifest.items()):
        fetch_document(client, args.out, category="laws", hash_=hash_, number=entry.get("number", ""),
                        name=entry.get("slug", hash_), manifest=manifest)
    save_manifest(os.path.join(args.out, "laws"), manifest)
    write_jsonl_index(args.out, "laws")
    write_jsonl_index(args.out, "codes")


def cmd_list_codes(args):
    for c in load_registry("codes_registry.json"):
        print(f"{c['number']:>10}  {c['date']}  {c['name']}")


def main():
    ap = argparse.ArgumentParser(prog="ruslaw-fetch", description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="./data", help="output data directory (default ./data)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("codes", help="fetch/update all RF codes")
    p.add_argument("--only", help="comma-separated registry keys/numbers to limit to")
    p.add_argument("--force", action="store_true", help="re-fetch even if manifest says current")
    p.set_defaults(func=cmd_codes)

    p = sub.add_parser("laws", help="fetch/update the curated federal-laws list")
    p.add_argument("--only", help="comma-separated registry keys to limit to")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_laws)

    p = sub.add_parser("law", help="fetch one specific law by number + name substring")
    p.add_argument("--number", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_law)

    p = sub.add_parser("update", help="incremental: discover + refresh since a date")
    p.add_argument("--since", required=True, help="YYYY-MM-DD")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("list-codes", help="print the codes registry")
    p.set_defaults(func=cmd_list_codes)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
