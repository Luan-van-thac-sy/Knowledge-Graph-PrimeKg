#!/usr/bin/env python3
"""
Query PrimeKG-style neighbors for a list of diagnoses and print a table.

Install:
  pip install neo4j tabulate

Set env:
  export NEO4J_URI="bolt://localhost:7687"
  export NEO4J_USER="neo4j"
  export NEO4J_PASSWORD="your_password"

Run:
  python query_diagnosis_neighbors.py \
    "Atrial Septal Defect, Type II" \
    "Iatrogenic Hypotension" \
    "History of Cardiovascular Disease" \
    "Hyperlipidemia" \
    --limit-per-diagnosis 10
"""

import os
import argparse
from neo4j import GraphDatabase
from tabulate import tabulate

QUERY = """
UNWIND $diagnoses AS dx
CALL {
  WITH dx
  MATCH (d)
  WHERE toLower(coalesce(d.name, d.display_name, d.label, "")) CONTAINS toLower(dx)

  OPTIONAL MATCH (d)-[r1]->(n1)
  WHERE type(r1) IN [
    "DISEASE_DISEASE",
    "DISEASE_PHENOTYPE_POSITIVE",
    "DISEASE_PHENOTYPE_NEGATIVE",
    "INDICATION",
    "CONTRAINDICATION",
    "OFF_LABEL_USE",
    "DRUG_EFFECT"
  ]

  RETURN
    coalesce(d.name, d.display_name, d.label) AS disease,
    type(r1) AS rel_1,
    coalesce(n1.name, n1.display_name, n1.label) AS neighbor_1,
    labels(n1) AS neighbor_1_labels
  LIMIT $limit_per_diagnosis
}
RETURN
  dx AS input_diagnosis,
  disease,
  rel_1,
  neighbor_1,
  neighbor_1_labels
ORDER BY input_diagnosis, disease, rel_1, neighbor_1
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query PrimeKG neighbors for one or more diagnoses"
    )
    parser.add_argument(
        "diagnoses",
        nargs="+",
        help="Diagnosis terms (pass multiple items as separate quoted args)",
    )
    parser.add_argument(
        "--limit-per-diagnosis",
        type=int,
        default=10,
        help="Max rows returned per input diagnosis (default: 10)",
    )
    args = parser.parse_args()

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise SystemExit("Error: NEO4J_PASSWORD is not set.")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            result = session.run(
                QUERY,
                diagnoses=args.diagnoses,
                limit_per_diagnosis=args.limit_per_diagnosis,
            )
            rows = [record.data() for record in result]
    finally:
        driver.close()

    if not rows:
        print("No matches found.")
        return

    print(tabulate(rows, headers="keys", tablefmt="github"))


if __name__ == "__main__":
    main()
