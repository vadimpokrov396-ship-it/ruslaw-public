"""Client for actual.pravo.gov.ru — the official "Тексты правовых актов с внесенными изменениями"
(texts of legal acts with amendments incorporated) service.

The site is a JS single-page app; there is no published API doc, so this client was built by
reading the app's own JS (config.js / common.js / list.js) rather than by brute-forcing endpoints.
Every call below mirrors an exact request the official web UI makes.

API base: http://actual.pravo.gov.ru:8000/api/ebpi/   (bpa=ebpi is the single public database id)

Flow to fetch the current text of a known document (identified by its `hash`, a 64-hex-char id
used throughout the site's URLs, e.g. .../content.html#hash=<hash>&ttl=1):
    1. card(hash)        -> {docid, docname, docpassing, docstate, ...}
    2. redactions(hash)  -> list of redaction records; the one with redactions["actual"]==True is
                             the current merged-with-amendments text; pick its `redid`.
    3. redtext(redid)    -> {"redtext": "<full HTML of that redaction>"}

To find a document you don't already have the hash for (e.g. "177-ФЗ о страховании вкладов"),
use attrsearch() with a document-number filter (+ a name substring to disambiguate, since law
numbers are reused every calendar year).
"""
import json
import time
import urllib.parse
import requests

API = "http://actual.pravo.gov.ru:8000/api/ebpi/"
BPA = "ebpi"

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36 ruslaw-fetch/0.1 "
    "(open dataset builder; source: https://github.com/vadimpokrov396-ship-it/ruslaw-public; "
    "contact: rubelforex@gmail.com)"
)


class ActualPravoClient:
    def __init__(self, ua=DEFAULT_UA, min_gap=2.0, timeout=25, session=None):
        self.ua = ua
        self.min_gap = min_gap
        self.timeout = timeout
        self.session = session or requests.Session()
        self._last_request_ts = 0.0

    def _get(self, path, params=None):
        wait = self.min_gap - (time.time() - self._last_request_ts)
        if wait > 0:
            time.sleep(wait)
        r = self.session.get(API + path, params=params, headers={"User-Agent": self.ua}, timeout=self.timeout)
        self._last_request_ts = time.time()
        r.raise_for_status()
        return r.json()

    def card(self, hash_):
        t = urllib.parse.quote(json.dumps({"hash": hash_}, ensure_ascii=False))
        return self._get(f"card/?bpa={BPA}&t={t}")

    def redactions(self, hash_, ttl=4):
        t = urllib.parse.quote(json.dumps({"hash": hash_, "ttl": ttl}, ensure_ascii=False))
        return self._get(f"redactions/?bpa={BPA}&t={t}")

    def redtext(self, redid, ttl=0):
        return self._get(f"redtext?bpa={BPA}&t={redid}&ttl={ttl}")

    def attrsearch(self, number=None, name_substr=None, extra_attrs=None):
        """Search the ~ full legislative database by document number (AttrId 4=kinds, 5=date,
        6=number, 7=name, 14=docstates). Returns raw {"docscount":N, "docs":[...]}.
        NOTE: pre-2000 "Закон РФ" acts store their number with a Roman "I" (e.g. "4468-I"), not
        an Arabic "1" ("4468-1") — try both if a search comes back empty.
        """
        attrs = []
        if number:
            attrs.append({"AttrId": 6, "AttrMode": 0, "Words": [number]})
        if name_substr:
            attrs.append({"AttrId": 7, "AttrMode": 9, "Words": [name_substr]})
        if extra_attrs:
            attrs.extend(extra_attrs)
        q = urllib.parse.quote(json.dumps(attrs, ensure_ascii=False))
        return self._get(f"attrsearch/?bpa={BPA}&q={q}")

    def find_hash(self, number, name_substr):
        """Convenience: returns (hash, human_title) for the first exact match, or None."""
        res = self.attrsearch(number=number, name_substr=name_substr)
        docs = res.get("docs", [])
        if not docs:
            return None
        d = docs[0]
        return d["dochash"], f"{d['docpassing']} {d['docnames']}".strip()

    def get_actual_redaction(self, hash_):
        """Returns (card, redaction_record_or_None, redtext_html_or_None).
        Falls back to the most recently completed redaction if no redaction is flagged
        'actual' (rare, e.g. for an act that has since been repealed)."""
        card = self.card(hash_)
        reds = self.redactions(hash_)
        candidates = [r for r in reds.get("redactions", []) if r.get("actual")]
        if not candidates:
            candidates = sorted(
                (r for r in reds.get("redactions", []) if r.get("redcompleted")),
                key=lambda r: r.get("reddate", ""), reverse=True,
            )[:1]
        if not candidates:
            return card, None, None
        red = candidates[0]
        text_resp = self.redtext(red["redid"])
        return card, red, text_resp.get("redtext")
