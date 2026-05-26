#!/usr/bin/env python3
"""
Batch-enrich data4LLM CSV with PrimeKG medical knowledge context.

Usage:
    python scripts/batch_enrich.py --input data4LLM.csv --output data4LLM_enriched.jsonl

Each output line is a JSON object with all original CSV fields plus
`medical_knowledge_context` containing the enriched PrimeKG blob.
"""
from __future__ import annotations

import ast
import json
import argparse
import sys
import os
from pathlib import Path

import pandas as pd
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.enrichment import EnricherOrchestrator


def _parse_list_col(value: object) -> list[str]:
    """Parse CSV column that may be a Python list repr or a plain string."""
    if isinstance(value, list):
        return [str(v) for v in value]
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [str(v) for v in parsed]
    except (ValueError, SyntaxError):
        pass
    return [value.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch enrich data4LLM with PrimeKG context")
    parser.add_argument("--input", required=True, help="Path to data4LLM CSV file")
    parser.add_argument("--output", required=True, help="Path for enriched JSONL output")
    parser.add_argument(
        "--limit-phenotypes", type=int, default=10,
        help="Max phenotypes per disease (default: 10)"
    )
    parser.add_argument(
        "--limit-comorbid", type=int, default=5,
        help="Max comorbid diseases per disease (default: 5)"
    )
    parser.add_argument(
        "--limit-indications", type=int, default=10,
        help="Max indicated drugs per disease (default: 10)"
    )
    parser.add_argument(
        "--limit-contraindications", type=int, default=10,
        help="Max contraindicated drugs per disease (default: 10)"
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    enricher = EnricherOrchestrator(
        limit_phenotypes=args.limit_phenotypes,
        limit_comorbid=args.limit_comorbid,
        limit_indications=args.limit_indications,
        limit_contraindications=args.limit_contraindications,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as fout:
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Enriching rows"):
            diagnoses = _parse_list_col(row.get("diagnose", ""))
            drugbank_ids = _parse_list_col(row.get("drugbank_id", ""))

            ctx = enricher.enrich(diagnoses=diagnoses, drugbank_ids=drugbank_ids)

            record = row.to_dict()
            record["medical_knowledge_context"] = ctx.to_dict()
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Done. Wrote {len(df)} enriched rows to {out_path}")


if __name__ == "__main__":
    main()
