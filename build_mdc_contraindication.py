#!/usr/bin/env python3
"""
Build MDC contraindication matrix (Disease x Drug) from PrimeKG in Neo4j,
and evaluate contraindicated drugs for a multi-disease patient profile.

Install:
  pip install neo4j pandas tabulate

Set env:
  export NEO4J_URI="bolt://localhost:7687"
  export NEO4J_USER="neo4j"
  export NEO4J_PASSWORD="your_password"

Examples:
  # Build and save full contraindication matrix
  python build_mdc_contraindication.py build --out mdc_contraindication.csv

  # Evaluate one patient with multiple diagnoses
  python build_mdc_contraindication.py evaluate \
    "diabetes" "hypertension" "chronic kidney disease" \
    --top 50
"""

from __future__ import annotations

import argparse
import os
from typing import List

import pandas as pd
from neo4j import GraphDatabase
from tabulate import tabulate

QUERY_CONTRA = """
MATCH (d)-[r]->(drug:Drug)
WHERE type(r) = "CONTRAINDICATION"
RETURN
  coalesce(d.name, d.display_name, d.label) AS disease,
  coalesce(drug.name, drug.display_name, drug.label) AS drug
"""

QUERY_MATCH_DISEASES = """
UNWIND $diagnoses AS dx
MATCH (d)
WHERE toLower(coalesce(d.name, d.display_name, d.label, "")) CONTAINS toLower(dx)
RETURN DISTINCT
  dx AS input_diagnosis,
  coalesce(d.name, d.display_name, d.label) AS matched_disease
ORDER BY input_diagnosis, matched_disease
"""


def get_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        raise SystemExit("Error: NEO4J_PASSWORD is not set.")
    return GraphDatabase.driver(uri, auth=(user, password))


def load_contra_pairs() -> pd.DataFrame:
    driver = get_driver()
    try:
        with driver.session() as session:
            rows = [r.data() for r in session.run(QUERY_CONTRA)]
    finally:
        driver.close()

    if not rows:
        return pd.DataFrame(columns=["disease", "drug"])

    df = pd.DataFrame(rows).dropna(subset=["disease", "drug"]).drop_duplicates()
    return df


def build_matrix(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    tmp = df.copy()
    tmp["value"] = 1
    matrix = tmp.pivot_table(
        index="disease",
        columns="drug",
        values="value",
        aggfunc="max",
        fill_value=0,
    )
    matrix = matrix.sort_index(axis=0).sort_index(axis=1)
    return matrix


def match_input_diseases(diagnoses: List[str]) -> pd.DataFrame:
    driver = get_driver()
    try:
        with driver.session() as session:
            rows = [r.data() for r in session.run(QUERY_MATCH_DISEASES, diagnoses=diagnoses)]
    finally:
        driver.close()
    return pd.DataFrame(rows)


def evaluate_patient_profile(matrix: pd.DataFrame, matched_diseases: List[str]) -> pd.DataFrame:
    if matrix.empty or not matched_diseases:
        return pd.DataFrame(columns=["drug", "mdc_score"])

    available = [d for d in matched_diseases if d in matrix.index]
    if not available:
        return pd.DataFrame(columns=["drug", "mdc_score"])

    sub = matrix.loc[available]
    # MDC_j = max_{d in D} M[d, j]
    scores = sub.max(axis=0)
    out = scores[scores > 0].sort_values(ascending=False).reset_index()
    out.columns = ["drug", "mdc_score"]
    return out


def cmd_build(args):
    df = load_contra_pairs()
    matrix = build_matrix(df)

    if matrix.empty:
        print("No CONTRAINDICATION edges found.")
        return

    out_path = args.out
    matrix.to_csv(out_path)
    print(f"Saved MDC contraindication matrix: {out_path}")
    print(f"Shape: diseases={matrix.shape[0]}, drugs={matrix.shape[1]}")


def cmd_evaluate(args):
    df = load_contra_pairs()
    matrix = build_matrix(df)

    if matrix.empty:
        print("No CONTRAINDICATION edges found.")
        return

    matched_df = match_input_diseases(args.diagnoses)
    if matched_df.empty:
        print("No disease nodes matched your input diagnoses.")
        return

    matched_diseases = matched_df["matched_disease"].drop_duplicates().tolist()

    print("\nMatched diagnoses in graph:")
    print(tabulate(matched_df, headers="keys", tablefmt="github", showindex=False))

    flagged = evaluate_patient_profile(matrix, matched_diseases)

    if flagged.empty:
        print("\nNo contraindicated drugs found for matched diseases.")
        return

    if args.top is not None:
        flagged = flagged.head(args.top)

    print("\nMDC contraindicated drugs (score=1 means contraindicated by >=1 disease):")
    print(tabulate(flagged, headers="keys", tablefmt="github", showindex=False))

    if args.out:
        flagged.to_csv(args.out, index=False)
        print(f"\nSaved flagged drugs: {args.out}")


def main():
    parser = argparse.ArgumentParser(
        description="Build/evaluate MDC contraindication matrix from PrimeKG (Neo4j)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Build and save full disease-drug contraindication matrix")
    p_build.add_argument("--out", default="mdc_contraindication.csv", help="Output CSV path")
    p_build.set_defaults(func=cmd_build)

    p_eval = sub.add_parser("evaluate", help="Evaluate contraindicated drugs for input diagnoses")
    p_eval.add_argument("diagnoses", nargs="+", help="List of diagnosis terms")
    p_eval.add_argument("--top", type=int, default=50, help="Show top N drugs (default: 50)")
    p_eval.add_argument("--out", default="", help="Optional CSV output for flagged drugs")
    p_eval.set_defaults(func=cmd_evaluate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
