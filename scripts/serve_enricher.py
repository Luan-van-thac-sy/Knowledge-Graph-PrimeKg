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
