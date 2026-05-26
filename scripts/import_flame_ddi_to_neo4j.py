"""
Import adverse (harmful) Flame DDI rows into Neo4j as :DRUG_DRUG edges.

Aligns with PrimeKG styling: ``display_relation`` matches synergistic rows from
PrimeKG, but is set to ``Adverse interaction`` here; CSV ``description`` is stored
on the relationship. Rows are filtered to ``ADVERSE_DDI_TYPES`` only.
"""
import argparse
import csv
import logging
import os
import sys
from typing import Dict, Iterable, List, Optional, Set

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db.neo4j_connector import get_connector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Flame DDI type ids treated as adverse / harmful interactions (exclude synergistic etc.)
ADVERSE_DDI_TYPES: Set[int] = {112, 73, 41, 29, 23, 63, 98, 95, 111}

# Same property PrimeKG uses on :DRUG_DRUG (e.g. "synergistic interaction")
FLAME_DRUG_DRUG_DISPLAY = "Adverse interaction"

DEFAULT_INPUT_CSV = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "Flame",
        "data",
        "data_process",
        "input",
        "ddi_data_all.csv",
    )
)

INSERT_BATCH_QUERY = """
UNWIND $rows AS row
MERGE (left_drug:Drug {id: row.drug1})
  ON CREATE SET left_drug.source = coalesce(left_drug.source, "flame_ddi")
MERGE (right_drug:Drug {id: row.drug2})
  ON CREATE SET right_drug.source = coalesce(right_drug.source, "flame_ddi")
MERGE (left_drug)-[rel:DRUG_DRUG {source: "flame_ddi", ddi_type: row.ddi_type, pattern: row.pattern}]->(right_drug)
SET rel.display_relation = $display_relation,
    rel.description = row.description,
    rel.source = "flame_ddi",
    rel.interaction_class = "adverse"
"""


def _normalize_row(raw_row: Dict[str, str]) -> Dict[str, str]:
    return {
        "drug1": (raw_row.get("drug1") or "").strip(),
        "drug2": (raw_row.get("drug2") or "").strip(),
        "description": (raw_row.get("description") or "").strip(),
        "ddi_type": (raw_row.get("type") or "").strip(),
        "pattern": (raw_row.get("pattern") or "").strip(),
    }


def _parse_ddi_type(code: str) -> Optional[int]:
    if not code:
        return None
    try:
        return int(code.strip())
    except ValueError:
        return None


def _read_batches(csv_path: str, batch_size: int) -> Iterable[List[Dict[str, str]]]:
    batch: List[Dict[str, str]] = []
    skipped_missing_drugs = 0
    skipped_non_adverse_type = 0
    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required_columns = {"drug1", "drug2", "description", "type", "pattern"}
        missing = required_columns.difference(set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"Missing required columns in CSV: {sorted(missing)}")

        for raw_row in reader:
            row = _normalize_row(raw_row)
            if not row["drug1"] or not row["drug2"]:
                skipped_missing_drugs += 1
                continue
            t = _parse_ddi_type(row["ddi_type"])
            if t is None or t not in ADVERSE_DDI_TYPES:
                skipped_non_adverse_type += 1
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                yield batch
                batch = []

    if batch:
        yield batch

    logger.info(
        "CSV filter (adverse types only %s): skipped %s rows (missing drug ids), "
        "%s rows (type not in ADVERSE_DDI_TYPES)",
        sorted(ADVERSE_DDI_TYPES),
        skipped_missing_drugs,
        skipped_non_adverse_type,
    )


def import_ddi(csv_path: str, batch_size: int, clear_existing: bool) -> None:
    db = get_connector()
    if not db.connect():
        raise RuntimeError("Failed to connect to Neo4j database")

    if clear_existing:
        logger.info("Deleting previous flame_ddi drug–drug edges (:DRUG_DRUG and legacy :DRUG_DRUG_INTERACTION)...")
        delete_query = """
        MATCH ()-[r]->()
        WHERE (type(r) = 'DRUG_DRUG' AND r.source = 'flame_ddi')
           OR (type(r) = 'DRUG_DRUG_INTERACTION' AND r.source = 'flame_ddi')
        DELETE r
        """
        result = db.execute_write_query(delete_query)
        if not result.get("success", False):
            raise RuntimeError(f"Failed to clear existing relationships: {result.get('error')}")

    total_rows = 0
    total_batches = 0
    for batch in _read_batches(csv_path=csv_path, batch_size=batch_size):
        result = db.execute_write_query(
            INSERT_BATCH_QUERY,
            {"rows": batch, "display_relation": FLAME_DRUG_DRUG_DISPLAY},
        )
        if not result.get("success", False):
            raise RuntimeError(f"Batch insert failed: {result.get('error')}")
        total_rows += len(batch)
        total_batches += 1
        logger.info("Imported batch %s (%s rows total)", total_batches, total_rows)

    logger.info("DDI import completed. Total rows processed: %s", total_rows)
    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Load adverse Flame DDI as :DRUG_DRUG (display_relation=Adverse interaction, description from CSV)."
        )
    )
    parser.add_argument(
        "--csv-path",
        default=DEFAULT_INPUT_CSV,
        help="Path to ddi_data_all.csv (default: Flame/data/data_process/input/ddi_data_all.csv)",
    )
    parser.add_argument("--batch-size", type=int, default=2000, help="Rows per batch write to Neo4j")
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Delete existing :DRUG_DRUG relationships with source=flame_ddi before import",
    )
    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        raise FileNotFoundError(f"CSV not found: {args.csv_path}")
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be > 0")

    import_ddi(csv_path=args.csv_path, batch_size=args.batch_size, clear_existing=args.clear_existing)


if __name__ == "__main__":
    main()
