# Design: PrimeKG Medical Knowledge Context Enricher

**Date:** 2026-05-26
**Status:** Approved

## Problem

The data4LLM dataset (MIMIC-IV patient records) drives an LLM drug-prescription task via a structured prompt template. The `[Medical Knowledge Context]` section currently has no content. This design enriches each patient row with PrimeKG-derived biomedical knowledge before it reaches the LLM.

## Input

`data4LLM.csv` rows with columns:
- `diagnose` — list of diagnosis name strings
- `drugbank_id` — list of DrugBank IDs for currently prescribed drugs
- `drug_name` — list of drug name strings
- `procedure`, `diag_id`, `pro_id`, `drug_id` — supporting columns

Enrichment anchors only on **current visit** data (not patient history).

## Output Schema

Each row gains a `medical_knowledge_context` JSON blob:

```json
{
  "causal_pathway": [
    { "disease": "Atrial Septal Defect", "phenotypes": ["shortness of breath", "fatigue", "cyanosis"] }
  ],
  "comorbid_diseases": [
    { "disease": "Atrial Septal Defect", "related": ["Pulmonary Hypertension", "Heart Failure"] }
  ],
  "indications": [
    { "disease": "Atrial Septal Defect", "indicated_drugs": ["Digoxin", "Furosemide"] }
  ],
  "contraindications": [
    { "disease": "Atrial Septal Defect", "contraindicated_drugs": ["Verapamil", "NSAIDs"] }
  ],
  "ddi_alerts": [
    { "drug1": "Digoxin", "drug2": "Furosemide", "interaction": "hypokalemia risk — monitor potassium" }
  ]
}
```

This blob is serialized into `<CAUSAL_KNOWLEDGE_STRING>` in the prompt template.

## Knowledge Aspects

Five aspects extracted from PrimeKG Neo4j:

| # | Aspect | Input anchor | PrimeKG relation | JSON key |
|---|--------|-------------|-----------------|---------|
| 1 | Causal Pathway | `diagnose` | `DISEASE_PHENOTYPE_POSITIVE` | `causal_pathway` |
| 3 | Comorbid Diseases | `diagnose` | `DISEASE_DISEASE` | `comorbid_diseases` |
| 4 | Drug Indications | `diagnose` | `INDICATION` | `indications` |
| 5 | Contraindications | `diagnose` | `CONTRAINDICATION` | `contraindications` |
| 7 | DDI Alerts | `drugbank_id` pairs | `DRUG_DRUG` (PrimeKG + Flame) | `ddi_alerts` |

## Architecture

```
data4LLM CSV
      │
      ▼
EnricherOrchestrator          (src/enrichment/enricher.py)
  ├── causal_pathway(diagnoses)
  ├── comorbid_diseases(diagnoses)
  ├── indications(diagnoses)
  ├── contraindications(diagnoses)
  └── ddi_alerts(drugbank_ids)
      │
      ├── BatchProcessor       (scripts/batch_enrich.py)
      │     input:  data4LLM.csv
      │     output: data4LLM_enriched.jsonl
      │
      └── FastAPI /enrich      (scripts/serve_enricher.py)
            POST { diagnoses: [...], drugbank_ids: [...] }
            → { medical_knowledge_context: {...} }
```

## Query Strategy

- Aspects 1, 3, 4, 5 anchor on diagnosis name strings using case-insensitive fuzzy `CONTAINS` match (consistent with existing `query_diagnosis_neighbors.py` pattern).
- Aspect 7 anchors on `Drug.id` exact match against DrugBank IDs; all pairwise combinations checked via `UNWIND` over the cross-product of the input drug list.
- DDI covers both PrimeKG-native `DRUG_DRUG` edges and Flame DDI `DRUG_DRUG {source: "flame_ddi"}` edges.
- Result limits are configurable per aspect (defaults: 10 phenotypes, 5 comorbidities, 10 indications, 10 contraindications, all DDI pairs).

## File Structure

```
src/
  enrichment/
    __init__.py
    enricher.py      — EnricherOrchestrator class with 5 aspect methods
    queries.py       — Cypher query constants
    schema.py        — dataclasses for typed output blobs
scripts/
  batch_enrich.py    — CLI batch processor (CSV in, JSONL out)
  serve_enricher.py  — FastAPI runtime endpoint
```

Existing `src/db/`, `src/etl/`, and all current scripts are untouched.

## Pipeline Modes

**Offline batch:** `python scripts/batch_enrich.py --input data4LLM.csv --output data4LLM_enriched.jsonl`

**Runtime inference:** `POST /enrich` with JSON body `{ "diagnoses": [...], "drugbank_ids": [...] }` returns the knowledge context blob.

Both modes share the same `EnricherOrchestrator` instance with a pooled Neo4j driver.
