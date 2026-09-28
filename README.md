# ruslaw-fetch + ruslaw-public

**RU:** Открытый инструмент для скачивания ТЕКУЩЕЙ (с учётом всех поправок) официальной редакции
кодексов и законов РФ + готовый бесплатный датасет (все 24 кодекса + 45 федеральных законов) для
проектов вроде проверки фактов в текстах, юридических RAG-систем, NLP по русскому праву и т.д.

**EN:** An open-source tool that downloads the CURRENT (amendments-merged) official redaction of
Russian codes and federal laws, plus a ready-made free dataset (all 24 codes + 45 federal laws)
for projects like fact-checking, legal RAG systems, Russian-law NLP, etc.

---

## Почему это нужно / Why this exists

Официальный архив публикаций `publication.pravo.gov.ru` хранит акты как **сканы-PDF без
текстового слоя** — только оригинальный текст на момент принятия, без слияния более поздних
поправок. Большинство существующих открытых корпусов (например,
[irlcode/RusLawOD](https://github.com/irlcode/RusLawOD)) берут данные именно оттуда — то есть
несут то же ограничение: исторические, неконсолидированные снимки текста.

Мы используем **другой** официальный сервис — `actual.pravo.gov.ru` («Тексты правовых актов с
внесенными изменениями») — отдельный государственный портал, который уже сливает все поправки в
единый актуальный текст. У сервиса нет опубликованного API — мы получили рабочий путь чтением
собственного JS-приложения сайта (`config.js`/`common.js`/`list.js`), а не перебором. Метод
задокументирован в `tool/ruslaw_fetch/actual_pravo.py`.

*(EN)* The official publication archive (`publication.pravo.gov.ru`) stores acts as scanned PDFs
with no text layer — the as-enacted text only, amendments not merged. Most existing open corpora
(e.g. [irlcode/RusLawOD](https://github.com/irlcode/RusLawOD)) scrape that same archive and
therefore share this limitation. We instead use a *different* official service —
`actual.pravo.gov.ru` — a separate government portal that already merges every amendment into one
current text. It has no published API; we found a working path by reading the site's own JS
(not by brute-forcing), documented in `tool/ruslaw_fetch/actual_pravo.py`.

## Похожие проекты / Related projects (credit)

- **[irlcode/RusLawOD](https://github.com/irlcode/RusLawOD)** ([HF dataset](https://huggingface.co/datasets/irlspbru/RusLawOD)) —
  the largest existing open corpus of Russian legislation (2017-2024 scrape of pravo.gov.ru,
  Akoma Ntoso/LegalDocML XML). Academic-grade, historical snapshots, **CC BY-NC 4.0** (non-
  commercial). Great for research on legislative *history*; not what you want for "what does the
  law say *today*" — which is exactly the gap this project fills.
- **[tarbagan/pravo](https://github.com/tarbagan/pravo)** — a pravo.gov.ru PDF parser with OCR;
  same underlying scanned-PDF limitation we hit and moved away from (see `data/../refbase` project
  notes: OCR of those PDFs was tried and abandoned as too slow/unreliable for our needs).
- **[DrobyshevDev/praxis](https://github.com/DrobyshevDev/praxis)** — a Russian-law RAG assistant
  with its own corpus of codes/laws; a potential downstream consumer of a dataset like this one.

We could not find any existing open, permissively-licensed tool or dataset built on
`actual.pravo.gov.ru`'s current-redaction API — as far as we can tell this is a novel source for
the open-data community.

## Что внутри / What's inside

```
tool/                      MIT-licensed Python package + CLI (ruslaw_fetch)
  ruslaw_fetch/
    actual_pravo.py        client for actual.pravo.gov.ru (current redaction)
    publication_pravo.py   client for publication.pravo.gov.ru (metadata, for incremental updates)
    articles.py            HTML -> plain text -> article-level records
    storage.py             resumable manifest + JSON/Markdown/JSONL writers
    cli.py                 `codes` / `laws` / `law` / `update` / `list-codes` commands
    codes_registry.json    all 24 RF codes (name, number, date, hash)
    laws_registry.json     curated federal-laws starter list (finance/tax/consumer/pensions/
                            housing/family/labour/traffic/digital assets)
data/
  codes/<slug>.json, .md   one file pair per code, full text + article-level split
  laws/<slug>.json, .md    one file pair per federal law
  codes.jsonl.gz, laws.jsonl.gz  flat, one-row-per-article index (RAG-friendly; `gunzip -k` to unpack)
.github/workflows/
  weekly-update.yml.disabled   a ready GitHub Actions workflow for a weekly `ruslaw-fetch update`
                                 run — renamed with `.disabled` so it does NOT run until you rename
                                 it to `.yml` and enable Actions on the repo yourself.
LICENSE-CODE                MIT (tool/ only)
LICENSE-DATA.md             legal status of the texts in data/ (public domain, RF Civil Code
                             Art. 1259(6)) + disclaimer
publish.sh                  one-shot script to create the public GitHub repo and push (see below)
```

## Установка и использование / Install & use

```bash
cd tool
pip install -r requirements.txt   # requests, beautifulsoup4

# скачать/обновить все 24 кодекса
python3 -m ruslaw_fetch --out ../data codes

# скачать только один кодекс
python3 -m ruslaw_fetch --out ../data codes --only nk_ch1,koap

# скачать/обновить всю подборку федеральных законов
python3 -m ruslaw_fetch --out ../data laws

# скачать один конкретный закон по номеру + фрагменту названия
python3 -m ruslaw_fetch --out ../data law --number 44-ФЗ --name "контрактной системе"

# инкрементальное обновление: найти новое с даты + обновить всё уже скачанное
python3 -m ruslaw_fetch --out ../data update --since 2026-09-01

# список всех кодексов в реестре
python3 -m ruslaw_fetch list-codes
```

Как библиотека:
```python
from ruslaw_fetch.actual_pravo import ActualPravoClient
c = ActualPravoClient()
hash_, title = c.find_hash("400-ФЗ", "страховых пенсиях")
card, red, html = c.get_actual_redaction(hash_)
```

## Вежливость / Politeness

- ≥2 секунды между запросами к одному хосту (настраивается, `min_gap`).
- Честный User-Agent с указанием проекта и контакта.
- `robots.txt` обоих доменов проверен вручную перед началом (никаких Disallow на используемые
  пути на момент сборки, 27.09.2026).
- Резюмируемо: `manifest.json` в каждой категории данных помнит `redid` последней скачанной
  редакции — повторный запуск скачивает заново только то, что реально изменилось.

## Дисклеймер / Disclaimer

Это не юридическая консультация. Это сырой текст официальных актов для справки/поиска, не его
толкование. Перед использованием в реальном решении сверяйтесь с действующей редакцией на
`actual.pravo.gov.ru` напрямую — редакции меняются. Подробности лицензии — `LICENSE-DATA.md`.

*(EN)* This is not legal advice. Raw official text for reference/retrieval, not interpretation.
Verify against the live `actual.pravo.gov.ru` before relying on it for anything consequential —
redactions change. License details in `LICENSE-DATA.md`.

## Связь с проектом refbase / Relationship to the `refbase` project

Мы также ведём `~/refbase/` — внутреннюю RAG-базу для проверки числовых утверждений в наших
статьях (Wikipedia CC-BY-SA + EU MiCA + справочные страницы cbr.ru/sfr.gov.ru/nalog.gov.ru +
ЭТИ ЖЕ кодексы/законы + гибридный поиск BM25+эмбеддинги). Мы **не сливаем** её с этим репозиторием:
у `refbase` смешанные лицензии (часть контента — CC-BY-SA с обязательной атрибуцией, не годится
как "чистый" публичный датасет без разбора по источникам) и она заточена под наш внутренний
пайплайн (эмбеддинги на своём сервере, наши форматы). `ruslaw-public` — наоборот, специально
"чистый" (только не-копирайтные официальные тексты + наш MIT-код), из него `refbase` при желании
может ЧИТАТЬ как один из источников. Если понадобится — можно опубликовать `refbase`'s
`actual_pravo_gov_ru`-часть отдельно тем же способом, но Wikipedia/EU-часть точно должна остаться
отдельно из-за атрибуции.

*(EN)* We also maintain `~/refbase/` — an internal RAG base for fact-checking numeric claims in
our articles (Wikipedia CC-BY-SA + EU MiCA + cbr.ru/sfr.gov.ru/nalog.gov.ru reference pages + THE
SAME codes/laws + hybrid BM25+embeddings search). We deliberately do **not** merge it into this
repo: `refbase` mixes licenses (some content is CC-BY-SA requiring attribution, so it isn't a
"clean" public dataset without careful per-source separation) and is shaped for our internal
pipeline (embeddings on our own server, our formats). `ruslaw-public` is, by design, the "clean"
half — official, non-copyrightable texts + our MIT code — and `refbase` can read from it as one
of its sources if useful.
