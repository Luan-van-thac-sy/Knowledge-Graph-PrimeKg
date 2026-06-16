# Disease display name matches any keyword token from the diagnosis
def _disease_name_matches_tokens(with_vars: str) -> str:
    return f"""
  WITH {with_vars}, toLower(coalesce(d.name, d.display_name, d.label, "")) AS dname
  WHERE ANY(token IN spec.tokens WHERE dname CONTAINS toLower(token))
"""


CAUSAL_PATHWAY_QUERY = """
UNWIND $diagnosis_specs AS spec
CALL {
  WITH spec
  MATCH (d:Disease)-[:DISEASE_PHENOTYPE_POSITIVE]->(p)
""" + _disease_name_matches_tokens("spec, d, p") + """
  RETURN spec.input_dx AS input_dx,
         coalesce(d.name, d.display_name, d.label) AS disease,
         coalesce(p.name, p.display_name, p.label) AS phenotype
  LIMIT $limit
}
RETURN input_dx, disease, phenotype
ORDER BY input_dx, disease, phenotype
"""

COMORBID_DISEASES_QUERY = """
UNWIND $diagnosis_specs AS spec
CALL {
  WITH spec
  MATCH (d:Disease)-[:DISEASE_DISEASE]->(d2:Disease)
""" + _disease_name_matches_tokens("spec, d, d2") + """
  RETURN spec.input_dx AS input_dx,
         coalesce(d.name, d.display_name, d.label) AS disease,
         coalesce(d2.name, d2.display_name, d2.label) AS related
  LIMIT $limit
}
RETURN input_dx, disease, related
ORDER BY input_dx, disease, related
"""

INDICATIONS_QUERY = """
UNWIND $diagnosis_specs AS spec
CALL {
  WITH spec
  MATCH (d)-[:INDICATION]->(drug:Drug)
""" + _disease_name_matches_tokens("spec, d, drug") + """
  RETURN spec.input_dx AS input_dx,
         coalesce(d.name, d.display_name, d.label) AS disease,
         coalesce(drug.name, drug.display_name, drug.label) AS drug_name
  LIMIT $limit
}
RETURN input_dx, disease, drug_name
ORDER BY input_dx, disease, drug_name
"""

CONTRAINDICATIONS_QUERY = """
UNWIND $diagnosis_specs AS spec
CALL {
  WITH spec
  MATCH (d)-[:CONTRAINDICATION]->(drug:Drug)
""" + _disease_name_matches_tokens("spec, d, drug") + """
  RETURN spec.input_dx AS input_dx,
         coalesce(d.name, d.display_name, d.label) AS disease,
         coalesce(drug.name, drug.display_name, drug.label) AS drug_name
  LIMIT $limit
}
RETURN input_dx, disease, drug_name
ORDER BY input_dx, disease, drug_name
"""

# Flame adverse DDI only (excludes PrimeKG e.g. "synergistic interaction")
DDI_QUERY = """
WITH $drug_ids AS ids
UNWIND ids AS id1
UNWIND ids AS id2
WITH id1, id2
WHERE id1 < id2
MATCH (d1:Drug {id: id1})-[r:DRUG_DRUG]-(d2:Drug {id: id2})
WHERE coalesce(r.display_relation, '') = 'Adverse interaction'
   OR coalesce(r.interaction_class, '') = 'adverse'
RETURN coalesce(d1.name, d1.display_name, d1.label, id1) AS drug1,
       coalesce(d2.name, d2.display_name, d2.label, id2) AS drug2,
       coalesce(r.display_relation, 'Adverse interaction') AS interaction,
       r.ddi_type AS ddi_type,
       r.pattern AS pattern
"""
