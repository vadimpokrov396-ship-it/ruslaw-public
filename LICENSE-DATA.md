# License and legal status of the data in `data/`

## What `data/` contains

The current, amendments-merged ("actual redaction") text of:
- all 24 codes of the Russian Federation (Гражданский, Налоговый, Трудовой, КоАП, etc.);
- ~49 federal laws and acts covering finance, taxation, consumer protection, pensions, housing,
  family, labour, road traffic and digital assets/crypto.

Sourced from **actual.pravo.gov.ru** ("Тексты правовых актов с внесенными изменениями"), the
official Russian government legal-information portal that merges every amendment into the current
text. This is a genuinely official government service — not a third-party compilation.

## Legal status of the texts themselves

Under the **Civil Code of the Russian Federation, Article 1259, paragraph 6** (Гражданский кодекс
РФ, ст. 1259 п. 6), the following are **not objects of copyright**:
> "official documents of state authorities and local self-government bodies of municipal
> formations, including laws, other legal texts, judicial decisions, other materials of a
> legislative, administrative and judicial character... as well as their official translations."

That means the *text of the laws and codes themselves* is public domain / not copyrightable in
Russia (and, by the nature of the material, not meaningfully copyrightable anywhere else either —
it is the literal wording of a country's statutes). You may copy, redistribute, modify the
formatting of, and build on this data freely, for any purpose, commercial or not.

## What we do NOT claim ownership of, and what we DO claim

- We (this repository's maintainers) claim **no copyright** over the legal texts in `data/`.
- We **do** claim copyright (MIT-licensed, see `LICENSE-CODE`) over the *code* in `tool/` — the
  scraper, parser, and CLI that produced this dataset — and over our own selection/curation of
  which acts to include and how the JSON/Markdown/JSONL files are structured.
- Redaction dates, `docstate` labels, and other metadata fields are copied verbatim from the
  official source's own API responses.

## What this is NOT

- **Not legal advice.** This is raw legal text for reference and retrieval, not an interpretation
  of it. Always verify against the live official source before relying on a specific figure or
  clause for a real decision — see "Staying current" below.
- **Not necessarily the in-force text at the moment you read it.** Redactions change (new laws
  amend old ones); each record carries its own `redaction_date` so you can tell how fresh it is.
  Re-run `ruslaw-fetch update --since <date>` to refresh.
- **Not a substitute for `actual.pravo.gov.ru` itself** for anything legally consequential — this
  dataset is a convenience snapshot of that official service, built and maintained by a third
  party (us), not by the Russian government.

## Staying current

Run `python3 -m ruslaw_fetch update --since YYYY-MM-DD` (see `tool/README.md`) to pull anything
published since your last run. A (disabled-by-default) GitHub Actions workflow for a weekly
automated refresh is included at `.github/workflows/weekly-update.yml.disabled`.
