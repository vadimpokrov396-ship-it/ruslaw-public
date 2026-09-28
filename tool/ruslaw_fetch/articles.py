"""Turn the raw redtext HTML (a full Word-exported document) into plain text and split it into
article-level records: [{"number": "220", "title": "...", "text": "..."}].

RF legal acts almost always number their articles "Статья N." (laws/codes) or "Пункт N."
(government resolutions like the traffic rules, Постановление 1090). We match both.
"""
import re
from bs4 import BeautifulSoup

ARTICLE_RE = re.compile(r"^(Статья\s+\d+[\.\d]*)\.?\s*(.*)$")
PUNKT_RE = re.compile(r"^(Пункт\s+\d+[\.\d]*)\.?\s*(.*)$")


def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # put every article/punkt header on its own paragraph boundary so downstream splitting is
    # clean, REGARDLESS of whether it was already preceded by a single (not blank-line) \n
    text = re.sub(r"\n*(Статья \d+[\.\d]*\.)", r"\n\n\1", text)
    text = re.sub(r"\n*(Пункт \d+[\.\d]*\.)", r"\n\n\1", text)
    return text


def split_articles(text):
    """Returns a list of {"number","title","text"} dicts, one per article/punkt found, plus a
    leading {"number": None, "title": "Преамбула", "text": ...} chunk for anything before the
    first article (adoption info, changing-acts list, etc.) if non-trivial."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    records = []
    preamble = []
    cur = None
    for p in paras:
        first_line = p.split("\n", 1)[0]
        m = ARTICLE_RE.match(first_line) or PUNKT_RE.match(first_line)
        if m:
            if cur:
                records.append(cur)
            number = re.sub(r"^(Статья|Пункт)\s+", "", m.group(1)).rstrip(".")
            title = m.group(2).strip()
            cur = {"number": number, "title": title, "text": p}
        else:
            if cur:
                cur["text"] += "\n\n" + p
            else:
                preamble.append(p)
    if cur:
        records.append(cur)
    if preamble and len("\n\n".join(preamble)) > 80:
        records.insert(0, {"number": None, "title": "Преамбула", "text": "\n\n".join(preamble)})
    return records
