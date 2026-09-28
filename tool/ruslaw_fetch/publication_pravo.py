"""Client for publication.pravo.gov.ru — the official publication portal. Used here only for
INCREMENTAL DISCOVERY: it exposes a documented Documents API (with a real swagger.json at
/swagger/v1/swagger.json) that lists newly-published federal laws by date range, which is a good
"what changed since I last ran this" signal even though publication.pravo.gov.ru itself only
serves scanned PDFs (no text layer) for the documents' *original* text — we use it purely to
discover *which* laws to re-check on actual.pravo.gov.ru, not to read text from it.
"""
import time
import requests

API = "http://publication.pravo.gov.ru/api/"
FZ_TYPE_ID = "82a8bf1c-3bc7-47ed-827f-7affd43a7f27"  # "Федеральный закон" in DocumentTypes


class PublicationPravoClient:
    def __init__(self, ua=None, min_gap=2.0, timeout=20, session=None):
        from .actual_pravo import DEFAULT_UA
        self.ua = ua or DEFAULT_UA
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

    def new_federal_laws_since(self, date_from, date_to=None, page_size=200):
        """date_from/date_to: 'YYYY-MM-DD'. Returns the raw Documents-API item list
        (number, name, documentDate, publishDateShort, ...) for newly published federal laws —
        use each item's `number` + `name` to look it up on actual.pravo.gov.ru via
        ActualPravoClient.find_hash().
        """
        params = {"DocumentTypes": FZ_TYPE_ID, "PageSize": page_size}
        if date_from:
            params["DocumentDateFrom"] = date_from
        if date_to:
            params["DocumentDateTo"] = date_to
        j = self._get("Documents", params=params)
        items = j.get("items", [])
        # NOTE (verified 27/09/2026): this API's DocumentDateFrom/DocumentDateTo params were
        # observed to be silently ignored in testing (always returns the newest `page_size`
        # items sorted by date, regardless of the requested range) — so we ALWAYS also filter
        # client-side here to guarantee correctness rather than trusting the server-side filter.
        if date_from:
            items = [it for it in items if it.get("documentDate", "") >= date_from]
        if date_to:
            items = [it for it in items if it.get("documentDate", "") <= date_to]
        return items
