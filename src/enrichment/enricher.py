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
