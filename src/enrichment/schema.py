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
