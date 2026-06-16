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
        {
            "drug1": "Digoxin",
            "drug2": "Furosemide",
            "interaction": "Adverse interaction",
            "ddi_type": "29",
            "pattern": "The risk or severity of .*",
        },
    ]
    result = enricher.ddi_alerts(["DB00390", "DB00695"])
    assert len(result) == 1
    assert result[0].drug1 == "Digoxin"
    assert result[0].drug2 == "Furosemide"
    assert result[0].interaction == "Adverse interaction"
    assert result[0].ddi_type == "29"
    assert result[0].pattern == "The risk or severity of .*"


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
