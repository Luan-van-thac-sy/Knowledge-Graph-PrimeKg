# PrimeKG Medical Knowledge Context Enricher — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `EnricherOrchestrator` that queries PrimeKG Neo4j for 5 knowledge aspects per patient row and injects them as a JSON blob into the `[Medical Knowledge Context]` LLM prompt section.

**Architecture:** A shared `EnricherOrchestrator` class (5 Cypher-backed methods) is consumed by both a CLI batch processor (`scripts/batch_enrich.py`) and a FastAPI runtime endpoint (`scripts/serve_enricher.py`). All Neo4j queries use the existing `Neo4jConnector` singleton from `src/db/neo4j_connector.py`.

**Tech Stack:** Python 3.8+, neo4j==5.13.0 (already installed), fastapi, uvicorn, pandas, pytest, unittest.mock

---

## File Map

| File | Status | Responsibility |
|------|--------|---------------|
| `src/enrichment/__init__.py` | Create | Package marker, exports `EnricherOrchestrator` |
| `src/enrichment/schema.py` | Create | Dataclasses for 5 output types + `MedicalKnowledgeContext.to_dict()` |
| `src/enrichment/queries.py` | Create | 5 Cypher query string constants |
| `src/enrichment/enricher.py` | Create | `EnricherOrchestrator` with `causal_pathway`, `comorbid_diseases`, `indications`, `contraindications`, `ddi_alerts`, `enrich` |
| `tests/__init__.py` | Create | Package marker |
| `tests/enrichment/__init__.py` | Create | Package marker |
| `tests/enrichment/test_enricher.py` | Create | Unit tests for all 6 public methods using mocked connector |
| `scripts/batch_enrich.py` | Create | CLI: reads data4LLM CSV, writes enriched JSONL |
| `scripts/serve_enricher.py` | Create | FastAPI app with `POST /enrich` endpoint |
| `requirements.txt` | Modify | Add `fastapi==0.104.1` and `uvicorn==0.24.0` |

---

## Task 1: Output schema dataclasses

**Files:**
- Create: `src/enrichment/schema.py`

- [ ] **Step 1: Create `src/enrichment/schema.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class CausalPathwayEntry:
    disease: str
    phenotypes: List[str]


@dataclass
class ComorbidDiseaseEntry:
    disease: str
    related: List[str]


@dataclass
class IndicationEntry:
    disease: str
    indicated_drugs: List[str]


@dataclass
class ContraindicationEntry:
    disease: str
    contraindicated_drugs: List[str]


@dataclass
class DDIAlert:
    drug1: str
    drug2: str
    interaction: str


@dataclass
class MedicalKnowledgeContext:
    causal_pathway: List[CausalPathwayEntry] = field(default_factory=list)
    comorbid_diseases: List[ComorbidDiseaseEntry] = field(default_factory=list)
    indications: List[IndicationEntry] = field(default_factory=list)
    contraindications: List[ContraindicationEntry] = field(default_factory=list)
    ddi_alerts: List[DDIAlert] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "causal_pathway": [
                {"disease": e.disease, "phenotypes": e.phenotypes}
                for e in self.causal_pathway
            ],
            "comorbid_diseases": [
                {"disease": e.disease, "related": e.related}
                for e in self.comorbid_diseases
            ],
            "indications": [
                {"disease": e.disease, "indicated_drugs": e.indicated_drugs}
                for e in self.indications
            ],
            "contraindications": [
                {"disease": e.disease, "contraindicated_drugs": e.contraindicated_drugs}
                for e in self.contraindications
            ],
            "ddi_alerts": [
                {"drug1": a.drug1, "drug2": a.drug2, "interaction": a.interaction}
                for a in self.ddi_alerts
            ],
        }
```

- [ ] **Step 2: Create `src/enrichment/__init__.py`**

```python
from .enricher import EnricherOrchestrator
from .schema import MedicalKnowledgeContext

__all__ = ["EnricherOrchestrator", "MedicalKnowledgeContext"]
```

- [ ] **Step 3: Commit**

```bash
git add src/enrichment/__init__.py src/enrichment/schema.py
git commit -m "feat: add enrichment schema dataclasses"
```

---

## Task 2: Cypher query constants

**Files:**
- Create: `src/enrichment/queries.py`

- [ ] **Step 1: Create `src/enrichment/queries.py`**

```python
CAUSAL_PATHWAY_QUERY = """
UNWIND $diagnoses AS dx
CALL {
  WITH dx
  MATCH (d:Disease)-[:DISEASE_PHENOTYPE_POSITIVE]->(p)
  WHERE toLower(coalesce(d.name, d.display_name, d.label, "")) CONTAINS toLower(dx)
  RETURN coalesce(d.name, d.display_name, d.label) AS disease,
         coalesce(p.name, p.display_name, p.label) AS phenotype
  LIMIT $limit
}
RETURN dx AS input_dx, disease, phenotype
ORDER BY input_dx, disease, phenotype
"""

COMORBID_DISEASES_QUERY = """
UNWIND $diagnoses AS dx
CALL {
  WITH dx
  MATCH (d:Disease)-[:DISEASE_DISEASE]->(d2:Disease)
  WHERE toLower(coalesce(d.name, d.display_name, d.label, "")) CONTAINS toLower(dx)
  RETURN coalesce(d.name, d.display_name, d.label) AS disease,
         coalesce(d2.name, d2.display_name, d2.label) AS related
  LIMIT $limit
}
RETURN dx AS input_dx, disease, related
ORDER BY input_dx, disease, related
"""

INDICATIONS_QUERY = """
UNWIND $diagnoses AS dx
CALL {
  WITH dx
  MATCH (d)-[:INDICATION]->(drug:Drug)
  WHERE toLower(coalesce(d.name, d.display_name, d.label, "")) CONTAINS toLower(dx)
  RETURN coalesce(d.name, d.display_name, d.label) AS disease,
         coalesce(drug.name, drug.display_name, drug.label) AS drug_name
  LIMIT $limit
}
RETURN dx AS input_dx, disease, drug_name
ORDER BY input_dx, disease, drug_name
"""

CONTRAINDICATIONS_QUERY = """
UNWIND $diagnoses AS dx
CALL {
  WITH dx
  MATCH (d)-[:CONTRAINDICATION]->(drug:Drug)
  WHERE toLower(coalesce(d.name, d.display_name, d.label, "")) CONTAINS toLower(dx)
  RETURN coalesce(d.name, d.display_name, d.label) AS disease,
         coalesce(drug.name, drug.display_name, drug.label) AS drug_name
  LIMIT $limit
}
RETURN dx AS input_dx, disease, drug_name
ORDER BY input_dx, disease, drug_name
"""

DDI_QUERY = """
WITH $drug_ids AS ids
UNWIND ids AS id1
UNWIND ids AS id2
WITH id1, id2
WHERE id1 < id2
MATCH (d1:Drug {id: id1})-[r:DRUG_DRUG]-(d2:Drug {id: id2})
RETURN coalesce(d1.name, d1.display_name, d1.label, id1) AS drug1,
       coalesce(d2.name, d2.display_name, d2.label, id2) AS drug2,
       coalesce(r.display_relation, r.description, "interaction") AS interaction
"""
```

- [ ] **Step 2: Commit**

```bash
git add src/enrichment/queries.py
git commit -m "feat: add Cypher query constants for 5 enrichment aspects"
```

---

## Task 3: Write failing tests for `EnricherOrchestrator`

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/enrichment/__init__.py`
- Create: `tests/enrichment/test_enricher.py`

- [ ] **Step 1: Create test package markers**

```bash
mkdir -p tests/enrichment
touch tests/__init__.py tests/enrichment/__init__.py
```

- [ ] **Step 2: Create `tests/enrichment/test_enricher.py`**

```python
from unittest.mock import MagicMock
import pytest

from src.enrichment.enricher import EnricherOrchestrator
from src.enrichment.schema import (
    CausalPathwayEntry,
    ComorbidDiseaseEntry,
    IndicationEntry,
    ContraindicationEntry,
    DDIAlert,
    MedicalKnowledgeContext,
)


@pytest.fixture
def mock_connector():
    return MagicMock()


@pytest.fixture
def enricher(mock_connector):
    return EnricherOrchestrator(connector=mock_connector)


# --- causal_pathway ---

def test_causal_pathway_groups_phenotypes_by_disease(enricher, mock_connector):
    mock_connector.execute_query.return_value = [
        {"input_dx": "heart failure", "disease": "Heart Failure", "phenotype": "fatigue"},
        {"input_dx": "heart failure", "disease": "Heart Failure", "phenotype": "dyspnea"},
        {"input_dx": "heart failure", "disease": "Heart Failure (HFrEF)", "phenotype": "reduced ejection fraction"},
    ]
    result = enricher.causal_pathway(["heart failure"])
    assert len(result) == 2
    hf = next(e for e in result if e.disease == "Heart Failure")
    assert set(hf.phenotypes) == {"fatigue", "dyspnea"}


def test_causal_pathway_empty_when_no_results(enricher, mock_connector):
    mock_connector.execute_query.return_value = []
    result = enricher.causal_pathway(["unknown disease xyz"])
    assert result == []


def test_causal_pathway_skips_none_phenotype(enricher, mock_connector):
    mock_connector.execute_query.return_value = [
        {"input_dx": "diabetes", "disease": "Diabetes Mellitus", "phenotype": None},
    ]
    result = enricher.causal_pathway(["diabetes"])
    assert result == []


# --- comorbid_diseases ---

def test_comorbid_diseases_groups_by_disease(enricher, mock_connector):
    mock_connector.execute_query.return_value = [
        {"input_dx": "hypertension", "disease": "Hypertension", "related": "Heart Failure"},
        {"input_dx": "hypertension", "disease": "Hypertension", "related": "Chronic Kidney Disease"},
    ]
    result = enricher.comorbid_diseases(["hypertension"])
    assert len(result) == 1
    assert set(result[0].related) == {"Heart Failure", "Chronic Kidney Disease"}


# --- indications ---

def test_indications_groups_drugs_by_disease(enricher, mock_connector):
    mock_connector.execute_query.return_value = [
        {"input_dx": "atrial fibrillation", "disease": "Atrial Fibrillation", "drug_name": "Warfarin"},
        {"input_dx": "atrial fibrillation", "disease": "Atrial Fibrillation", "drug_name": "Digoxin"},
    ]
    result = enricher.indications(["atrial fibrillation"])
    assert len(result) == 1
    assert set(result[0].indicated_drugs) == {"Warfarin", "Digoxin"}


# --- contraindications ---

def test_contraindications_groups_drugs_by_disease(enricher, mock_connector):
    mock_connector.execute_query.return_value = [
        {"input_dx": "renal failure", "disease": "Renal Failure", "drug_name": "NSAIDs"},
        {"input_dx": "renal failure", "disease": "Renal Failure", "drug_name": "Metformin"},
    ]
    result = enricher.contraindications(["renal failure"])
    assert len(result) == 1
    assert set(result[0].contraindicated_drugs) == {"NSAIDs", "Metformin"}


# --- ddi_alerts ---

def test_ddi_alerts_returns_interactions(enricher, mock_connector):
    mock_connector.execute_query.return_value = [
        {"drug1": "Digoxin", "drug2": "Furosemide", "interaction": "hypokalemia"},
    ]
    result = enricher.ddi_alerts(["DB00390", "DB00695"])
    assert len(result) == 1
    assert result[0].drug1 == "Digoxin"
    assert result[0].drug2 == "Furosemide"
    assert result[0].interaction == "hypokalemia"


def test_ddi_alerts_empty_for_single_drug(enricher, mock_connector):
    result = enricher.ddi_alerts(["DB00390"])
    mock_connector.execute_query.assert_not_called()
    assert result == []


def test_ddi_alerts_empty_for_no_drugbank_ids(enricher, mock_connector):
    result = enricher.ddi_alerts([])
    mock_connector.execute_query.assert_not_called()
    assert result == []


# --- enrich (orchestrator) ---

def test_enrich_returns_medical_knowledge_context(enricher, mock_connector):
    mock_connector.execute_query.return_value = []
    ctx = enricher.enrich(diagnoses=["heart failure"], drugbank_ids=["DB00390"])
    assert isinstance(ctx, MedicalKnowledgeContext)


def test_enrich_to_dict_has_all_keys(enricher, mock_connector):
    mock_connector.execute_query.return_value = []
    ctx = enricher.enrich(diagnoses=["heart failure"], drugbank_ids=[])
    d = ctx.to_dict()
    assert set(d.keys()) == {
        "causal_pathway", "comorbid_diseases", "indications",
        "contraindications", "ddi_alerts"
    }
```

- [ ] **Step 3: Run tests — verify they all fail with ImportError**

```bash
cd /Users/harvey/Personal/LVTS/Knowledge-Graph-PrimeKg
python -m pytest tests/enrichment/test_enricher.py -v 2>&1 | head -30
```

Expected: `ImportError: cannot import name 'EnricherOrchestrator' from 'src.enrichment.enricher'`

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/__init__.py tests/enrichment/__init__.py tests/enrichment/test_enricher.py
git commit -m "test: add failing tests for EnricherOrchestrator"
```

---

## Task 4: Implement `EnricherOrchestrator`

**Files:**
- Create: `src/enrichment/enricher.py`

- [ ] **Step 1: Create `src/enrichment/enricher.py`**

```python
from __future__ import annotations

import sys
import os
from collections import defaultdict
from typing import List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.neo4j_connector import Neo4jConnector, get_connector
from src.enrichment.queries import (
    CAUSAL_PATHWAY_QUERY,
    COMORBID_DISEASES_QUERY,
    INDICATIONS_QUERY,
    CONTRAINDICATIONS_QUERY,
    DDI_QUERY,
)
from src.enrichment.schema import (
    CausalPathwayEntry,
    ComorbidDiseaseEntry,
    IndicationEntry,
    ContraindicationEntry,
    DDIAlert,
    MedicalKnowledgeContext,
)


class EnricherOrchestrator:
    def __init__(
        self,
        connector: Optional[Neo4jConnector] = None,
        limit_phenotypes: int = 10,
        limit_comorbid: int = 5,
        limit_indications: int = 10,
        limit_contraindications: int = 10,
    ):
        self._connector = connector or get_connector()
        self._limit_phenotypes = limit_phenotypes
        self._limit_comorbid = limit_comorbid
        self._limit_indications = limit_indications
        self._limit_contraindications = limit_contraindications

    def causal_pathway(self, diagnoses: List[str]) -> List[CausalPathwayEntry]:
        if not diagnoses:
            return []
        rows = self._connector.execute_query(
            CAUSAL_PATHWAY_QUERY,
            {"diagnoses": diagnoses, "limit": self._limit_phenotypes},
        )
        grouped: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            disease = row.get("disease")
            phenotype = row.get("phenotype")
            if disease and phenotype:
                grouped[disease].append(phenotype)
        return [CausalPathwayEntry(disease=d, phenotypes=p) for d, p in grouped.items()]

    def comorbid_diseases(self, diagnoses: List[str]) -> List[ComorbidDiseaseEntry]:
        if not diagnoses:
            return []
        rows = self._connector.execute_query(
            COMORBID_DISEASES_QUERY,
            {"diagnoses": diagnoses, "limit": self._limit_comorbid},
        )
        grouped: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            disease = row.get("disease")
            related = row.get("related")
            if disease and related:
                grouped[disease].append(related)
        return [ComorbidDiseaseEntry(disease=d, related=r) for d, r in grouped.items()]

    def indications(self, diagnoses: List[str]) -> List[IndicationEntry]:
        if not diagnoses:
            return []
        rows = self._connector.execute_query(
            INDICATIONS_QUERY,
            {"diagnoses": diagnoses, "limit": self._limit_indications},
        )
        grouped: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            disease = row.get("disease")
            drug = row.get("drug_name")
            if disease and drug:
                grouped[disease].append(drug)
        return [IndicationEntry(disease=d, indicated_drugs=drugs) for d, drugs in grouped.items()]

    def contraindications(self, diagnoses: List[str]) -> List[ContraindicationEntry]:
        if not diagnoses:
            return []
        rows = self._connector.execute_query(
            CONTRAINDICATIONS_QUERY,
            {"diagnoses": diagnoses, "limit": self._limit_contraindications},
        )
        grouped: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            disease = row.get("disease")
            drug = row.get("drug_name")
            if disease and drug:
                grouped[disease].append(drug)
        return [ContraindicationEntry(disease=d, contraindicated_drugs=drugs) for d, drugs in grouped.items()]

    def ddi_alerts(self, drugbank_ids: List[str]) -> List[DDIAlert]:
        if len(drugbank_ids) < 2:
            return []
        rows = self._connector.execute_query(
            DDI_QUERY,
            {"drug_ids": drugbank_ids},
        )
        return [
            DDIAlert(
                drug1=row["drug1"],
                drug2=row["drug2"],
                interaction=row.get("interaction", "interaction"),
            )
            for row in rows
            if row.get("drug1") and row.get("drug2")
        ]

    def enrich(self, diagnoses: List[str], drugbank_ids: List[str]) -> MedicalKnowledgeContext:
        return MedicalKnowledgeContext(
            causal_pathway=self.causal_pathway(diagnoses),
            comorbid_diseases=self.comorbid_diseases(diagnoses),
            indications=self.indications(diagnoses),
            contraindications=self.contraindications(diagnoses),
            ddi_alerts=self.ddi_alerts(drugbank_ids),
        )
```

- [ ] **Step 2: Run tests — verify they all pass**

```bash
python -m pytest tests/enrichment/test_enricher.py -v
```

Expected output (all green):
```
tests/enrichment/test_enricher.py::test_causal_pathway_groups_phenotypes_by_disease PASSED
tests/enrichment/test_enricher.py::test_causal_pathway_empty_when_no_results PASSED
tests/enrichment/test_enricher.py::test_causal_pathway_skips_none_phenotype PASSED
tests/enrichment/test_enricher.py::test_comorbid_diseases_groups_by_disease PASSED
tests/enrichment/test_enricher.py::test_indications_groups_drugs_by_disease PASSED
tests/enrichment/test_enricher.py::test_contraindications_groups_drugs_by_disease PASSED
tests/enrichment/test_enricher.py::test_ddi_alerts_returns_interactions PASSED
tests/enrichment/test_enricher.py::test_ddi_alerts_empty_for_single_drug PASSED
tests/enrichment/test_enricher.py::test_ddi_alerts_empty_for_no_drugbank_ids PASSED
tests/enrichment/test_enricher.py::test_enrich_returns_medical_knowledge_context PASSED
tests/enrichment/test_enricher.py::test_enrich_to_dict_has_all_keys PASSED
```

- [ ] **Step 3: Commit**

```bash
git add src/enrichment/enricher.py
git commit -m "feat: implement EnricherOrchestrator with 5 PrimeKG aspect methods"
```

---

## Task 5: Batch CSV processor

**Files:**
- Create: `scripts/batch_enrich.py`

- [ ] **Step 1: Create `scripts/batch_enrich.py`**

```python
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
```

- [ ] **Step 2: Verify script parses args correctly (dry run with --help)**

```bash
python scripts/batch_enrich.py --help
```

Expected: shows usage with `--input`, `--output`, limit flags.

- [ ] **Step 3: Commit**

```bash
git add scripts/batch_enrich.py
git commit -m "feat: add batch_enrich CLI for offline CSV enrichment"
```

---

## Task 6: FastAPI runtime endpoint

**Files:**
- Modify: `requirements.txt`
- Create: `scripts/serve_enricher.py`

- [ ] **Step 1: Add FastAPI and uvicorn to `requirements.txt`**

Add these two lines at the end of `requirements.txt`:
```
fastapi==0.104.1
uvicorn==0.24.0
```

- [ ] **Step 2: Install new dependencies**

```bash
pip install fastapi==0.104.1 uvicorn==0.24.0
```

Expected: installs successfully.

- [ ] **Step 3: Create `scripts/serve_enricher.py`**

```python
#!/usr/bin/env python3
"""
FastAPI runtime enrichment endpoint.

Start:
    python scripts/serve_enricher.py
    # or
    uvicorn scripts.serve_enricher:app --host 0.0.0.0 --port 8001

POST /enrich
    Body: { "diagnoses": ["Heart Failure"], "drugbank_ids": ["DB00390", "DB00695"] }
    Returns: { "medical_knowledge_context": { ... } }
"""
from __future__ import annotations

import sys
import os
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel

from src.enrichment import EnricherOrchestrator

app = FastAPI(title="PrimeKG Enricher", version="0.1.0")

_enricher: EnricherOrchestrator | None = None


def _get_enricher() -> EnricherOrchestrator:
    global _enricher
    if _enricher is None:
        _enricher = EnricherOrchestrator()
    return _enricher


class EnrichRequest(BaseModel):
    diagnoses: List[str]
    drugbank_ids: List[str] = []


class EnrichResponse(BaseModel):
    medical_knowledge_context: dict


@app.post("/enrich", response_model=EnrichResponse)
def enrich(request: EnrichRequest) -> EnrichResponse:
    ctx = _get_enricher().enrich(
        diagnoses=request.diagnoses,
        drugbank_ids=request.drugbank_ids,
    )
    return EnrichResponse(medical_knowledge_context=ctx.to_dict())


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

- [ ] **Step 4: Verify FastAPI app loads without error**

```bash
python -c "from scripts.serve_enricher import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt scripts/serve_enricher.py
git commit -m "feat: add FastAPI /enrich runtime endpoint"
```

---

## Task 7: Final integration check

- [ ] **Step 1: Run the full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all 11 tests pass, 0 failures.

- [ ] **Step 2: Verify batch script help text**

```bash
python scripts/batch_enrich.py --help
```

Expected: shows `--input`, `--output`, and 4 limit flags.

- [ ] **Step 3: Smoke test FastAPI endpoint (requires Neo4j running)**

If Neo4j is available:
```bash
# Terminal 1
python scripts/serve_enricher.py &

# Terminal 2
curl -s -X POST http://localhost:8001/enrich \
  -H "Content-Type: application/json" \
  -d '{"diagnoses": ["Heart Failure"], "drugbank_ids": ["DB00390", "DB00695"]}' \
  | python -m json.tool
```

Expected: JSON response with `medical_knowledge_context` containing all 5 keys.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: verify enricher integration end-to-end"
```
