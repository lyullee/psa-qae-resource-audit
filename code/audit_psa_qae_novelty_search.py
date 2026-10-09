"""Archive a bounded Crossref/OpenAlex screen for direct PSA--QAE precedents.

This is a reproducible metadata screen, not a systematic-review claim.  It
does not submit QPU work or use private credentials.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
OUT_JSON = OUT / "PSA_QAE_CCE_NOVELTY_SEARCH_AUDIT.json"
OUT_MD = OUT / "PSA_QAE_CCE_NOVELTY_SEARCH_AUDIT.md"

QUERIES = [
    '"pressure swing adsorption" "quantum amplitude estimation"',
    '"pressure swing adsorption" quantum computing optimization',
    '"quantum amplitude estimation" adsorption process',
    '"quantum amplitude estimation" chemical process optimization',
]
ROWS_PER_QUERY = 50
USER_AGENT = "psa-qae-literature-audit/1.0 (bounded scholarly-metadata screen)"


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def clean_markup(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def crossref_records(query: str) -> list[dict[str, object]]:
    params = urllib.parse.urlencode({"query.bibliographic": query, "rows": ROWS_PER_QUERY})
    data = fetch_json(f"https://api.crossref.org/works?{params}")
    records = []
    for item in data.get("message", {}).get("items", []):
        title = " ".join(item.get("title") or []).strip()
        if not title:
            continue
        date_parts = (item.get("published-print") or item.get("published-online") or item.get("issued") or {}).get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        doi = item.get("DOI")
        records.append({
            "source": "Crossref",
            "query": query,
            "title": title,
            "abstract": clean_markup(item.get("abstract")),
            "year": year,
            "doi": doi,
            "url": f"https://doi.org/{doi}" if doi else item.get("URL"),
            "publisher": item.get("publisher"),
            "type": item.get("type"),
        })
    return records


def openalex_abstract(inverted: dict[str, list[int]] | None) -> str:
    if not inverted:
        return ""
    positioned = [(position, word) for word, positions in inverted.items() for position in positions]
    return " ".join(word for _, word in sorted(positioned))


def openalex_records(query: str) -> list[dict[str, object]]:
    params = urllib.parse.urlencode({"search": query, "per-page": ROWS_PER_QUERY})
    data = fetch_json(f"https://api.openalex.org/works?{params}")
    records = []
    for item in data.get("results", []):
        title = (item.get("display_name") or "").strip()
        if not title:
            continue
        doi_url = item.get("doi")
        doi = doi_url.removeprefix("https://doi.org/") if doi_url else None
        location = item.get("primary_location") or {}
        source = location.get("source") or {}
        records.append({
            "source": "OpenAlex",
            "query": query,
            "title": title,
            "abstract": openalex_abstract(item.get("abstract_inverted_index")),
            "year": item.get("publication_year"),
            "doi": doi,
            "url": doi_url or item.get("id"),
            "publisher": source.get("display_name"),
            "type": item.get("type"),
        })
    return records


def direct_psa_qae(record: dict[str, object]) -> bool:
    searchable = f"{record.get('title', '')} {record.get('abstract', '')}".casefold()
    psa = any(term in searchable for term in ("pressure swing adsorption", "vacuum swing adsorption", "cyclic adsorption"))
    qae = any(term in searchable for term in ("quantum amplitude estimation", "maximum-likelihood amplitude estimation", "maximum likelihood amplitude estimation"))
    return psa and qae


def deduplicate(records: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    for record in records:
        key = str(record.get("doi") or record.get("title", "")).casefold()
        if key not in merged:
            merged[key] = record | {"sources": [record["source"]], "queries": [record["query"]]}
        else:
            current = merged[key]
            current["sources"] = sorted(set(current["sources"]) | {record["source"]})
            current["queries"] = sorted(set(current["queries"]) | {record["query"]})
            if len(str(record.get("abstract", ""))) > len(str(current.get("abstract", ""))):
                current["abstract"] = record.get("abstract", "")
    for record in merged.values():
        record.pop("source", None)
        record.pop("query", None)
        record["direct_psa_qae_metadata_match"] = direct_psa_qae(record)
    return sorted(merged.values(), key=lambda row: (str(row.get("year") or ""), str(row["title"]).casefold()), reverse=True)


def main() -> None:
    records: list[dict[str, object]] = []
    source_counts: dict[str, dict[str, int]] = {}
    for query in QUERIES:
        crossref = crossref_records(query)
        openalex = openalex_records(query)
        records.extend(crossref)
        records.extend(openalex)
        source_counts[query] = {"Crossref": len(crossref), "OpenAlex": len(openalex)}

    unique = deduplicate(records)
    direct = [record for record in unique if record["direct_psa_qae_metadata_match"]]
    payload = {
        "schema": "psa-qae-cce-novelty-search-audit/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "search_date": "2026-10-09",
        "scope": "bounded scholarly-metadata screen; not an exhaustive systematic review",
        "sources": {
            "Crossref": "https://api.crossref.org/works",
            "OpenAlex": "https://api.openalex.org/works",
        },
        "queries": QUERIES,
        "rows_requested_per_query_per_source": ROWS_PER_QUERY,
        "retrieved_counts": source_counts,
        "deduplicated_record_count": len(unique),
        "direct_match_rule": "metadata contains a PSA/cyclic-adsorption phrase and an explicit QAE/MLAE phrase",
        "direct_psa_qae_match_count": len(direct),
        "direct_matches": direct,
        "claim_boundary": (
            "No direct cyclic multicomponent PSA plus QAE/MLAE chance-constraint case was identified "
            "in this bounded screen. This does not prove universal absence or priority."
        ),
        "records": unique,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# CCE novelty-search audit: PSA plus QAE",
        "",
        f"Search date: `{payload['search_date']}`",
        "",
        f"Scope: {payload['scope']}.",
        "",
        "## Queries",
        "",
        *[f"- `{query}`" for query in QUERIES],
        "",
        "## Machine-readable metadata result",
        "",
        f"Crossref and OpenAlex returned `{len(records)}` query-result records and `{len(unique)}` unique records after DOI/title deduplication.",
        f"The explicit metadata rule returned `{len(direct)}` direct PSA-plus-QAE/MLAE matches.",
        "",
        "The metadata result is a reproducible screen, not proof of absence. Candidate records were also checked at publisher, DOI, repository, or preprint pages and separated into QAE/risk methods, process-quantum precedents, and classical PSA optimisation. Quantum molecular-sieving papers were excluded because they concern material selectivity rather than gate-based probability estimation.",
        "",
        "## Allowed wording",
        "",
        payload["claim_boundary"],
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "complete_bounded_screen",
        "records_retrieved": len(records),
        "unique_records": len(unique),
        "direct_psa_qae_matches": len(direct),
        "outputs": [str(OUT_JSON), str(OUT_MD)],
    }, indent=2))


if __name__ == "__main__":
    main()
