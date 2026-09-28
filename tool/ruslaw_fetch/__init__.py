"""ruslaw-fetch: an open-source, polite downloader for the CURRENT (amendments-merged) text of
Russian federal laws and codes from the official government portal actual.pravo.gov.ru, plus
official publication metadata from publication.pravo.gov.ru for incremental updates.

Why this exists: pravo.gov.ru's official publication archive stores each act as a scanned PDF
with no text layer (the as-originally-enacted text, not the current amended version). Most public
scrapers (e.g. irlcode/RusLawOD) mine that same archive and therefore carry the SAME limitation —
historical, non-consolidated snapshots. actual.pravo.gov.ru is a separate official service (also
government-run) that already merges every amendment into a single "actual redaction" text — this
tool downloads THAT, which is what almost anyone checking "what does the law say today" needs.

License: MIT (this code). The downloaded legal texts themselves are official texts of legal acts
and are not objects of copyright under Russian law (Civil Code of the Russian Federation,
Article 1259(6)) — see LICENSE-DATA.md.
"""

__version__ = "0.1.0"
