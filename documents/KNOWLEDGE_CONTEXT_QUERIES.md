# Knowledge Context Queries - PrimeKG

Tài liệu hướng dẫn sử dụng Cypher queries để truy xuất thông tin knowledge context từ PrimeKG database trong Neo4j.

## Mục lục

1. [Tổng quan](#tổng-quan)
2. [Causal Pathway Queries](#1-causal-pathway-queries)
3. [Causal Neighbors Queries](#2-causal-neighbors-queries)
4. [DDI Considerations Queries](#3-ddi-considerations-queries)
5. [MDC Considerations Queries](#4-mdc-considerations-queries)
6. [Combined Knowledge Context Queries](#5-combined-knowledge-context-queries)

---

## Tổng quan

Knowledge context trong PrimeKG được chia thành 4 thành phần chính:

1. **Causal Pathway**: Giúp mô hình biết bệnh nhân bị bệnh gì và nên dùng thuốc gì
   - Relations: `disease_phenotype_positive`, `indication`

2. **Causal Neighbors**: Giúp mô hình hiểu ngữ cảnh bệnh lý phức tạp
   - Relations: `disease_disease`, `phenotype_phenotype`

3. **DDI Considerations**: Kiểm tra tương tác giữa các thuốc (Drug-Drug Interactions)
   - Relations: `drug_drug`, `drug_effect`

4. **MDC Considerations**: Kiểm tra thuốc có kỵ với bệnh không (Medical Disease Contraindications)
   - Relations: `contraindication`

---

## 1. Causal Pathway Queries

### 1.1. Tìm phenotypes liên quan đến một disease (disease_phenotype_positive)

#### 1.1.1. Tìm theo disease ID (property id)

```cypher
// Tìm tất cả phenotypes dương tính liên quan đến một disease cụ thể (theo property id)
MATCH (dis:Disease {id: $disease_id})-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
RETURN dis.id as disease_id,
       dis.name as disease_name,
       p.id as phenotype_id,
       p.name as phenotype_name,
       r.display_relation as display_relation
ORDER BY p.name;
```

**Ví dụ sử dụng:**
```cypher
MATCH (dis:Disease {id: '5044'})-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
RETURN dis.name as disease_name,
       p.name as phenotype_name,
       r.display_relation
LIMIT 10;
```

#### 1.1.2. Tìm theo internal Neo4j ID

```cypher
// Tìm theo internal Neo4j ID (nếu bạn có internal ID từ graph visualization)
MATCH (dis:Disease)-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
WHERE elementId(dis) = $internal_id OR toString(id(dis)) = $internal_id
RETURN dis.id as disease_id,
       dis.name as disease_name,
       p.id as phenotype_id,
       p.name as phenotype_name,
       r.display_relation as display_relation
ORDER BY p.name;
```

**Ví dụ sử dụng với internal ID:**
```cypher
// Nếu internal ID là 3573
MATCH (dis:Disease)-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
WHERE id(dis) = 3573
RETURN dis.id as disease_id,
       dis.name as disease_name,
       p.id as phenotype_id,
       p.name as phenotype_name,
       r.display_relation as display_relation
ORDER BY p.name;
```

#### 1.1.3. Tìm theo tên bệnh (hỗ trợ fuzzy matching)

```cypher
// Tìm tất cả phenotypes dương tính liên quan đến một disease theo tên (hỗ trợ fuzzy matching)
MATCH (dis:Disease)-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
WHERE toLower(dis.name) = toLower($disease_name)
   OR toLower(dis.name) CONTAINS toLower($disease_name)
   OR toLower($disease_name) CONTAINS toLower(dis.name)
RETURN dis.id as disease_id,
       dis.name as disease_name,
       p.id as phenotype_id,
       p.name as phenotype_name,
       r.display_relation as display_relation,
       CASE 
           WHEN toLower(dis.name) = toLower($disease_name) THEN 'EXACT_MATCH'
           WHEN toLower(dis.name) CONTAINS toLower($disease_name) OR toLower($disease_name) CONTAINS toLower(dis.name) THEN 'PARTIAL_MATCH'
           ELSE 'SIMILAR'
       END as match_type
ORDER BY 
    CASE 
        WHEN toLower(dis.name) = toLower($disease_name) THEN 1
        WHEN toLower(dis.name) CONTAINS toLower($disease_name) OR toLower($disease_name) CONTAINS toLower(dis.name) THEN 2
        ELSE 3
    END,
    p.name;
```

**Ví dụ sử dụng theo tên:**
```cypher
// Tìm với tên bệnh "osteogenesis imperfecta"
MATCH (dis:Disease)-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
WHERE toLower(dis.name) = toLower('osteogenesis imperfecta')
   OR toLower(dis.name) CONTAINS toLower('osteogenesis imperfecta')
   OR toLower('osteogenesis imperfecta') CONTAINS toLower(dis.name)
RETURN dis.id as disease_id,
       dis.name as disease_name,
       p.id as phenotype_id,
       p.name as phenotype_name,
       r.display_relation as display_relation
ORDER BY p.name
LIMIT 20;
```

#### 1.1.4. Tìm property id từ internal ID

```cypher
// Nếu bạn có internal ID (ví dụ: 3573) và muốn biết property id thực sự
MATCH (dis:Disease)
WHERE id(dis) = 3573
RETURN dis.id as actual_disease_id, 
       dis.name as disease_name,
       id(dis) as internal_id;
// Sau đó dùng actual_disease_id trong query 1.1.1
```

### 1.2. Tìm diseases có phenotype cụ thể

```cypher
// Tìm tất cả diseases có phenotype dương tính cụ thể
MATCH (dis:Disease)-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype {id: $phenotype_id})
RETURN dis.id as disease_id,
       dis.name as disease_name,
       p.id as phenotype_id,
       p.name as phenotype_name
ORDER BY dis.name;
```

### 1.3. Tìm drugs được chỉ định cho một disease (indication)

```cypher
// Tìm tất cả drugs được chỉ định điều trị một disease
MATCH (d:Drug)-[r:INDICATION]->(dis:Disease {id: $disease_id})
RETURN d.id as drug_id,
       d.name as drug_name,
       dis.id as disease_id,
       dis.name as disease_name,
       r.display_relation as display_relation
ORDER BY d.name;
```

**Ví dụ sử dụng:**
```cypher
MATCH (d:Drug)-[r:INDICATION]->(dis:Disease {id: '5044'})
RETURN d.name as drug_name,
       dis.name as disease_name,
       r.display_relation
LIMIT 10;
```

### 1.4. Tìm diseases mà một drug được chỉ định điều trị

```cypher
// Tìm tất cả diseases mà một drug được chỉ định
MATCH (d:Drug {id: $drug_id})-[r:INDICATION]->(dis:Disease)
RETURN d.id as drug_id,
       d.name as drug_name,
       dis.id as disease_id,
       dis.name as disease_name
ORDER BY dis.name;
```

### 1.5. Causal Pathway đầy đủ: Disease → Phenotype → Drug

```cypher
// Tìm pathway đầy đủ từ disease qua phenotype đến drug
MATCH (dis:Disease {id: $disease_id})-[r1:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
MATCH (d:Drug)-[r2:INDICATION]->(dis)
RETURN dis.id as disease_id,
       dis.name as disease_name,
       p.id as phenotype_id,
       p.name as phenotype_name,
       d.id as drug_id,
       d.name as drug_name,
       r1.display_relation as phenotype_relation,
       r2.display_relation as drug_relation
ORDER BY d.name, p.name;
```

### 1.6. Tìm top phenotypes phổ biến nhất cho một disease

```cypher
// Tìm top N phenotypes phổ biến nhất liên quan đến một disease
MATCH (dis:Disease {id: $disease_id})-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
WITH p, count(r) as phenotype_count
RETURN p.id as phenotype_id,
       p.name as phenotype_name,
       phenotype_count
ORDER BY phenotype_count DESC
LIMIT $limit;
```

### 1.7. Tìm top drugs được chỉ định nhiều nhất cho một disease

```cypher
// Tìm top N drugs được chỉ định nhiều nhất cho một disease
MATCH (d:Drug)-[r:INDICATION]->(dis:Disease {id: $disease_id})
WITH d, count(r) as indication_count
RETURN d.id as drug_id,
       d.name as drug_name,
       d.source as drug_source,
       indication_count
ORDER BY indication_count DESC
LIMIT $limit;
```

---

## 2. Causal Neighbors Queries

### 2.1. Tìm diseases liên quan đến một disease (disease_disease)

```cypher
// Tìm tất cả diseases liên quan đến một disease cụ thể
MATCH (dis1:Disease {id: $disease_id})-[r:DISEASE_DISEASE]-(dis2:Disease)
RETURN dis1.id as disease_id,
       dis1.name as disease_name,
       dis2.id as related_disease_id,
       dis2.name as related_disease_name,
       r.display_relation as display_relation
ORDER BY dis2.name;
```

**Ví dụ sử dụng:**
```cypher
MATCH (dis1:Disease {id: '5044'})-[r:DISEASE_DISEASE]-(dis2:Disease)
RETURN dis1.name as disease_name,
       dis2.name as related_disease_name,
       r.display_relation
LIMIT 10;
```

### 2.2. Tìm diseases có mối quan hệ mạnh nhất

```cypher
// Tìm diseases có nhiều mối quan hệ với diseases khác nhất
MATCH (dis1:Disease)-[r:DISEASE_DISEASE]-(dis2:Disease)
WITH dis1, count(DISTINCT dis2) as related_diseases_count
RETURN dis1.id as disease_id,
       dis1.name as disease_name,
       related_diseases_count
ORDER BY related_diseases_count DESC
LIMIT 20;
```

### 2.3. Tìm phenotypes liên quan đến một phenotype (phenotype_phenotype)

```cypher
// Tìm tất cả phenotypes liên quan đến một phenotype cụ thể
MATCH (p1:Effect_phenotype {id: $phenotype_id})-[r:PHENOTYPE_PHENOTYPE]-(p2:Effect_phenotype)
RETURN p1.id as phenotype_id,
       p1.name as phenotype_name,
       p2.id as related_phenotype_id,
       p2.name as related_phenotype_name,
       r.display_relation as display_relation
ORDER BY p2.name;
```

**Ví dụ sử dụng:**
```cypher
MATCH (p1:Effect_phenotype)-[r:PHENOTYPE_PHENOTYPE]-(p2:Effect_phenotype)
RETURN p1.name as phenotype_name,
       p2.name as related_phenotype_name,
       r.display_relation
LIMIT 10;
```

### 2.4. Tìm phenotypes có mối quan hệ mạnh nhất

```cypher
// Tìm phenotypes có nhiều mối quan hệ với phenotypes khác nhất
MATCH (p1:Effect_phenotype)-[r:PHENOTYPE_PHENOTYPE]-(p2:Effect_phenotype)
WITH p1, count(DISTINCT p2) as related_phenotypes_count
RETURN p1.id as phenotype_id,
       p1.name as phenotype_name,
       related_phenotypes_count
ORDER BY related_phenotypes_count DESC
LIMIT 20;
```

### 2.5. Tìm ngữ cảnh bệnh lý phức tạp: Disease và các diseases liên quan

```cypher
// Tìm một disease và tất cả diseases liên quan (để hiểu ngữ cảnh phức tạp)
MATCH (dis:Disease {id: $disease_id})
OPTIONAL MATCH (dis)-[r:DISEASE_DISEASE]-(related_dis:Disease)
RETURN dis.id as disease_id,
       dis.name as disease_name,
       collect(DISTINCT {
           related_disease_id: related_dis.id,
           related_disease_name: related_dis.name,
           relation: r.display_relation
       }) as related_diseases;
```

### 2.6. Tìm ngữ cảnh phenotype phức tạp: Phenotype và các phenotypes liên quan

```cypher
// Tìm một phenotype và tất cả phenotypes liên quan
MATCH (p:Effect_phenotype {id: $phenotype_id})
OPTIONAL MATCH (p)-[r:PHENOTYPE_PHENOTYPE]-(related_p:Effect_phenotype)
RETURN p.id as phenotype_id,
       p.name as phenotype_name,
       collect(DISTINCT {
           related_phenotype_id: related_p.id,
           related_phenotype_name: related_p.name,
           relation: r.display_relation
       }) as related_phenotypes;
```

### 2.7. Tìm diseases có cùng phenotypes (ngữ cảnh bệnh lý tương tự)

```cypher
// Tìm diseases có chung phenotypes (có thể có ngữ cảnh bệnh lý tương tự)
MATCH (dis1:Disease {id: $disease_id})-[r1:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)<-[r2:DISEASE_PHENOTYPE_POSITIVE]-(dis2:Disease)
WHERE dis1.id <> dis2.id
WITH dis1, dis2, count(DISTINCT p) as common_phenotypes
WHERE common_phenotypes >= 2
RETURN dis1.name as disease_name,
       dis2.name as similar_disease_name,
       common_phenotypes
ORDER BY common_phenotypes DESC
LIMIT 20;
```

---

## 3. DDI Considerations Queries

### 3.1. Tìm drugs tương tác với một drug (drug_drug)

```cypher
// Tìm tất cả drugs có tương tác với một drug cụ thể
MATCH (d1:Drug {id: $drug_id})-[r:DRUG_DRUG]-(d2:Drug)
RETURN d1.id as drug_id,
       d1.name as drug_name,
       d2.id as interacting_drug_id,
       d2.name as interacting_drug_name,
       r.display_relation as display_relation
ORDER BY d2.name;
```

**Ví dụ sử dụng:**
```cypher
MATCH (d1:Drug {id: 'DB00903'})-[r:DRUG_DRUG]-(d2:Drug)
RETURN d1.name as drug_name,
       d2.name as interacting_drug_name,
       r.display_relation
LIMIT 10;
```

### 3.2. Kiểm tra tương tác giữa hai drugs cụ thể

```cypher
// Kiểm tra xem hai drugs có tương tác với nhau không
MATCH (d1:Drug {id: $drug1_id})-[r:DRUG_DRUG]-(d2:Drug {id: $drug2_id})
RETURN d1.id as drug1_id,
       d1.name as drug1_name,
       d2.id as drug2_id,
       d2.name as drug2_name,
       r.display_relation as interaction_type,
       CASE WHEN r IS NOT NULL THEN 'CÓ TƯƠNG TÁC' ELSE 'KHÔNG CÓ TƯƠNG TÁC' END as interaction_status;
```

### 3.3. Tìm drugs có nhiều tương tác nhất

```cypher
// Tìm drugs có nhiều tương tác với drugs khác nhất (cần cẩn thận khi kê đơn)
MATCH (d1:Drug)-[r:DRUG_DRUG]-(d2:Drug)
WITH d1, count(DISTINCT d2) as interaction_count
RETURN d1.id as drug_id,
       d1.name as drug_name,
       d1.source as drug_source,
       interaction_count
ORDER BY interaction_count DESC
LIMIT 20;
```

### 3.4. Tìm effects của một drug (drug_effect)

```cypher
// Tìm tất cả effects (tác dụng/phản ứng) của một drug
MATCH (d:Drug {id: $drug_id})-[r:DRUG_EFFECT]->(e:Effect)
RETURN d.id as drug_id,
       d.name as drug_name,
       e.id as effect_id,
       e.name as effect_name,
       r.display_relation as display_relation
ORDER BY e.name;
```

**Ví dụ sử dụng:**
```cypher
MATCH (d:Drug {id: 'DB00903'})-[r:DRUG_EFFECT]->(e:Effect)
RETURN d.name as drug_name,
       e.name as effect_name,
       r.display_relation
LIMIT 10;
```

### 3.5. Tìm drugs có effect cụ thể

```cypher
// Tìm tất cả drugs có một effect cụ thể
MATCH (d:Drug)-[r:DRUG_EFFECT]->(e:Effect {id: $effect_id})
RETURN d.id as drug_id,
       d.name as drug_name,
       e.id as effect_id,
       e.name as effect_name
ORDER BY d.name;
```

### 3.6. Kiểm tra an toàn khi kết hợp nhiều drugs

```cypher
// Kiểm tra tương tác giữa các drugs trong một danh sách
MATCH (d1:Drug)
WHERE d1.id IN $drug_ids
MATCH (d2:Drug)
WHERE d2.id IN $drug_ids AND d1.id < d2.id
OPTIONAL MATCH (d1)-[r:DRUG_DRUG]-(d2)
RETURN d1.id as drug1_id,
       d1.name as drug1_name,
       d2.id as drug2_id,
       d2.name as drug2_name,
       CASE WHEN r IS NOT NULL THEN r.display_relation ELSE 'KHÔNG CÓ TƯƠNG TÁC' END as interaction_status
ORDER BY d1.name, d2.name;
```

**Ví dụ sử dụng:**
```cypher
MATCH (d1:Drug)
WHERE d1.id IN ['DB00903', 'DB00887', 'DB00641']
MATCH (d2:Drug)
WHERE d2.id IN ['DB00903', 'DB00887', 'DB00641'] AND d1.id < d2.id
OPTIONAL MATCH (d1)-[r:DRUG_DRUG]-(d2)
RETURN d1.name as drug1_name,
       d2.name as drug2_name,
       CASE WHEN r IS NOT NULL THEN r.display_relation ELSE 'KHÔNG CÓ TƯƠNG TÁC' END as interaction_status;
```

### 3.7. Tìm drugs có effects tương tự

```cypher
// Tìm drugs có chung effects (có thể có tác dụng tương tự)
MATCH (d1:Drug {id: $drug_id})-[r1:DRUG_EFFECT]->(e:Effect)<-[r2:DRUG_EFFECT]-(d2:Drug)
WHERE d1.id <> d2.id
WITH d1, d2, count(DISTINCT e) as common_effects
WHERE common_effects >= 2
RETURN d1.name as drug_name,
       d2.name as similar_drug_name,
       common_effects
ORDER BY common_effects DESC
LIMIT 20;
```

---

## 4. MDC Considerations Queries

### 4.1. Tìm drugs chống chỉ định cho một disease (contraindication)

```cypher
// Tìm tất cả drugs chống chỉ định cho một disease cụ thể
MATCH (d:Drug)-[r:CONTRAINDICATION]->(dis:Disease {id: $disease_id})
RETURN d.id as drug_id,
       d.name as drug_name,
       dis.id as disease_id,
       dis.name as disease_name,
       r.display_relation as display_relation
ORDER BY d.name;
```

**Ví dụ sử dụng:**
```cypher
MATCH (d:Drug)-[r:CONTRAINDICATION]->(dis:Disease {id: '5044'})
RETURN d.name as drug_name,
       dis.name as disease_name,
       r.display_relation
LIMIT 10;
```

### 4.2. Tìm diseases mà một drug chống chỉ định

```cypher
// Tìm tất cả diseases mà một drug chống chỉ định
MATCH (d:Drug {id: $drug_id})-[r:CONTRAINDICATION]->(dis:Disease)
RETURN d.id as drug_id,
       d.name as drug_name,
       dis.id as disease_id,
       dis.name as disease_name
ORDER BY dis.name;
```

**Ví dụ sử dụng:**
```cypher
MATCH (d:Drug {id: 'DB00903'})-[r:CONTRAINDICATION]->(dis:Disease)
RETURN d.name as drug_name,
       dis.name as disease_name,
       r.display_relation
LIMIT 10;
```

### 4.3. Kiểm tra drug có chống chỉ định với disease không

```cypher
// Kiểm tra xem một drug có chống chỉ định với một disease không
MATCH (d:Drug {id: $drug_id})
MATCH (dis:Disease {id: $disease_id})
OPTIONAL MATCH (d)-[r:CONTRAINDICATION]->(dis)
RETURN d.id as drug_id,
       d.name as drug_name,
       dis.id as disease_id,
       dis.name as disease_name,
       CASE WHEN r IS NOT NULL THEN 'CHỐNG CHỈ ĐỊNH' ELSE 'AN TOÀN' END as contraindication_status,
       r.display_relation as contraindication_detail;
```

### 4.4. Tìm drugs an toàn cho một disease (không có contraindication)

```cypher
// Tìm drugs được chỉ định cho disease nhưng không có chống chỉ định
MATCH (d:Drug)-[r1:INDICATION]->(dis:Disease {id: $disease_id})
WHERE NOT EXISTS {
    MATCH (d)-[r2:CONTRAINDICATION]->(dis)
}
RETURN d.id as drug_id,
       d.name as drug_name,
       dis.id as disease_id,
       dis.name as disease_name,
       r1.display_relation as indication_type
ORDER BY d.name;
```

### 4.5. Tìm drugs có nhiều chống chỉ định nhất

```cypher
// Tìm drugs có nhiều chống chỉ định nhất (cần cẩn thận khi kê đơn)
MATCH (d:Drug)-[r:CONTRAINDICATION]->(dis:Disease)
WITH d, count(DISTINCT dis) as contraindication_count
RETURN d.id as drug_id,
       d.name as drug_name,
       d.source as drug_source,
       contraindication_count
ORDER BY contraindication_count DESC
LIMIT 20;
```

### 4.6. Kiểm tra an toàn khi kê đơn drug cho bệnh nhân có nhiều diseases

```cypher
// Kiểm tra xem một drug có chống chỉ định với bất kỳ disease nào trong danh sách không
MATCH (d:Drug {id: $drug_id})
MATCH (dis:Disease)
WHERE dis.id IN $disease_ids
OPTIONAL MATCH (d)-[r:CONTRAINDICATION]->(dis)
WITH d, collect({
    disease_id: dis.id,
    disease_name: dis.name,
    is_contraindicated: r IS NOT NULL,
    contraindication_detail: r.display_relation
}) as disease_checks
RETURN d.id as drug_id,
       d.name as drug_name,
       disease_checks,
       size([check IN disease_checks WHERE check.is_contraindicated = true]) as contraindication_count,
       CASE 
           WHEN size([check IN disease_checks WHERE check.is_contraindicated = true]) > 0 
           THEN 'CÓ CHỐNG CHỈ ĐỊNH' 
           ELSE 'AN TOÀN' 
       END as safety_status;
```

**Ví dụ sử dụng:**
```cypher
MATCH (d:Drug {id: 'DB00903'})
MATCH (dis:Disease)
WHERE dis.id IN ['5044', '5391', '5027']
OPTIONAL MATCH (d)-[r:CONTRAINDICATION]->(dis)
RETURN d.name as drug_name,
       dis.name as disease_name,
       CASE WHEN r IS NOT NULL THEN 'CHỐNG CHỈ ĐỊNH' ELSE 'AN TOÀN' END as status;
```

---

## 5. Combined Knowledge Context Queries

### 5.1. Tổng hợp knowledge context đầy đủ cho một disease

```cypher
// Tổng hợp tất cả knowledge context cho một disease: 
// - Causal Pathway (phenotypes, drugs được chỉ định)
// - Causal Neighbors (diseases liên quan)
// - MDC (drugs chống chỉ định)
MATCH (dis:Disease {id: $disease_id})
OPTIONAL MATCH (dis)-[r1:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
OPTIONAL MATCH (d_ind:Drug)-[r2:INDICATION]->(dis)
OPTIONAL MATCH (dis)-[r3:DISEASE_DISEASE]-(related_dis:Disease)
OPTIONAL MATCH (d_contra:Drug)-[r4:CONTRAINDICATION]->(dis)
RETURN dis.id as disease_id,
       dis.name as disease_name,
       collect(DISTINCT {
           type: 'phenotype',
           id: p.id,
           name: p.name,
           relation: r1.display_relation
       }) as phenotypes,
       collect(DISTINCT {
           type: 'indicated_drug',
           id: d_ind.id,
           name: d_ind.name,
           relation: r2.display_relation
       }) as indicated_drugs,
       collect(DISTINCT {
           type: 'related_disease',
           id: related_dis.id,
           name: related_dis.name,
           relation: r3.display_relation
       }) as related_diseases,
       collect(DISTINCT {
           type: 'contraindicated_drug',
           id: d_contra.id,
           name: d_contra.name,
           relation: r4.display_relation
       }) as contraindicated_drugs;
```

### 5.2. Tổng hợp knowledge context đầy đủ cho một drug

```cypher
// Tổng hợp tất cả knowledge context cho một drug:
// - Causal Pathway (diseases được chỉ định)
// - DDI (drugs tương tác, effects)
// - MDC (diseases chống chỉ định)
MATCH (d:Drug {id: $drug_id})
OPTIONAL MATCH (d)-[r1:INDICATION]->(dis_ind:Disease)
OPTIONAL MATCH (d)-[r2:DRUG_DRUG]-(d_interact:Drug)
OPTIONAL MATCH (d)-[r3:DRUG_EFFECT]->(e:Effect)
OPTIONAL MATCH (d)-[r4:CONTRAINDICATION]->(dis_contra:Disease)
RETURN d.id as drug_id,
       d.name as drug_name,
       collect(DISTINCT {
           type: 'indicated_disease',
           id: dis_ind.id,
           name: dis_ind.name,
           relation: r1.display_relation
       }) as indicated_diseases,
       collect(DISTINCT {
           type: 'interacting_drug',
           id: d_interact.id,
           name: d_interact.name,
           relation: r2.display_relation
       }) as interacting_drugs,
       collect(DISTINCT {
           type: 'effect',
           id: e.id,
           name: e.name,
           relation: r3.display_relation
       }) as effects,
       collect(DISTINCT {
           type: 'contraindicated_disease',
           id: dis_contra.id,
           name: dis_contra.name,
           relation: r4.display_relation
       }) as contraindicated_diseases;
```

### 5.3. Drug recommendation với kiểm tra an toàn đầy đủ

```cypher
// Tìm drugs được chỉ định cho disease và kiểm tra:
// - Có chống chỉ định không?
// - Có tương tác với drugs khác không?
// - Có effects gì?
MATCH (d:Drug)-[r_ind:INDICATION]->(dis:Disease {id: $disease_id})
OPTIONAL MATCH (d)-[r_contra:CONTRAINDICATION]->(dis)
OPTIONAL MATCH (d)-[r_ddi:DRUG_DRUG]-(d_interact:Drug)
WHERE d_interact.id IN $other_drugs OR $other_drugs = []
OPTIONAL MATCH (d)-[r_effect:DRUG_EFFECT]->(e:Effect)
RETURN d.id as drug_id,
       d.name as drug_name,
       dis.name as disease_name,
       r_ind.display_relation as indication_type,
       CASE WHEN r_contra IS NOT NULL THEN 'CHỐNG CHỈ ĐỊNH' ELSE 'AN TOÀN' END as contraindication_status,
       collect(DISTINCT {
           drug_id: d_interact.id,
           drug_name: d_interact.name,
           interaction: r_ddi.display_relation
       }) as drug_interactions,
       collect(DISTINCT {
           effect_id: e.id,
           effect_name: e.name,
           relation: r_effect.display_relation
       }) as drug_effects
ORDER BY d.name;
```

### 5.4. Tìm drugs an toàn và hiệu quả cho một disease

```cypher
// Tìm drugs được chỉ định cho disease, không có chống chỉ định, 
// và có ít tương tác với drugs khác
MATCH (d:Drug)-[r_ind:INDICATION]->(dis:Disease {id: $disease_id})
WHERE NOT EXISTS {
    MATCH (d)-[:CONTRAINDICATION]->(dis)
}
WITH d, dis, r_ind, 
     size([(d)-[:DRUG_DRUG]-(other:Drug) | other]) as interaction_count
RETURN d.id as drug_id,
       d.name as drug_name,
       dis.name as disease_name,
       r_ind.display_relation as indication_type,
       interaction_count,
       CASE 
           WHEN interaction_count = 0 THEN 'RẤT AN TOÀN'
           WHEN interaction_count <= 3 THEN 'AN TOÀN'
           ELSE 'CẦN CẨN THẬN'
       END as safety_level
ORDER BY interaction_count ASC, d.name
LIMIT 20;
```

### 5.5. So sánh drugs cho một disease với đầy đủ knowledge context

```cypher
// So sánh nhiều drugs cho một disease với đầy đủ thông tin:
// - Indication strength
// - Contraindications
// - Drug interactions
// - Effects
MATCH (dis:Disease {id: $disease_id})
MATCH (d:Drug)
WHERE d.id IN $drug_ids
OPTIONAL MATCH (d)-[r_ind:INDICATION]->(dis)
OPTIONAL MATCH (d)-[r_contra:CONTRAINDICATION]->(dis)
OPTIONAL MATCH (d)-[r_ddi:DRUG_DRUG]-(d_interact:Drug)
WHERE d_interact.id IN $drug_ids
OPTIONAL MATCH (d)-[r_effect:DRUG_EFFECT]->(e:Effect)
RETURN d.id as drug_id,
       d.name as drug_name,
       CASE WHEN r_ind IS NOT NULL THEN 'CÓ CHỈ ĐỊNH' ELSE 'KHÔNG CÓ CHỈ ĐỊNH' END as indication_status,
       r_ind.display_relation as indication_type,
       CASE WHEN r_contra IS NOT NULL THEN 'CHỐNG CHỈ ĐỊNH' ELSE 'AN TOÀN' END as contraindication_status,
       size(collect(DISTINCT d_interact)) as interaction_count,
       collect(DISTINCT e.name) as effects
ORDER BY 
    CASE WHEN r_ind IS NOT NULL THEN 0 ELSE 1 END,
    CASE WHEN r_contra IS NOT NULL THEN 1 ELSE 0 END,
    interaction_count ASC;
```

---

## Sử dụng trong Python

### Ví dụ: Lấy Causal Pathway cho một disease

```python
from src.db.neo4j_connector import get_connector

db = get_connector()
db.connect()

# Query 1: Lấy phenotypes và drugs được chỉ định
query = """
MATCH (dis:Disease {id: $disease_id})-[r1:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
MATCH (d:Drug)-[r2:INDICATION]->(dis)
RETURN dis.name as disease_name,
       collect(DISTINCT p.name) as phenotypes,
       collect(DISTINCT d.name) as indicated_drugs
"""

result = db.execute_read_query(query, {'disease_id': '5044'})
print(result)
```

### Ví dụ: Kiểm tra DDI cho danh sách drugs

```python
# Kiểm tra tương tác giữa các drugs
query = """
MATCH (d1:Drug)
WHERE d1.id IN $drug_ids
MATCH (d2:Drug)
WHERE d2.id IN $drug_ids AND d1.id < d2.id
OPTIONAL MATCH (d1)-[r:DRUG_DRUG]-(d2)
RETURN d1.name as drug1_name,
       d2.name as drug2_name,
       CASE WHEN r IS NOT NULL THEN r.display_relation ELSE 'KHÔNG CÓ TƯƠNG TÁC' END as interaction
"""

result = db.execute_read_query(query, {
    'drug_ids': ['DB00903', 'DB00887', 'DB00641']
})
print(result)
```

### Ví dụ: Kiểm tra MDC cho drug và disease

```python
# Kiểm tra chống chỉ định
query = """
MATCH (d:Drug {id: $drug_id})
MATCH (dis:Disease {id: $disease_id})
OPTIONAL MATCH (d)-[r:CONTRAINDICATION]->(dis)
RETURN d.name as drug_name,
       dis.name as disease_name,
       CASE WHEN r IS NOT NULL THEN 'CHỐNG CHỈ ĐỊNH' ELSE 'AN TOÀN' END as status
"""

result = db.execute_read_query(query, {
    'drug_id': 'DB00903',
    'disease_id': '5044'
})
print(result)
```

---

## Tips và Best Practices

1. **Sử dụng parameters**: Luôn sử dụng parameters (`$variable`) thay vì hardcode values để tránh injection và tăng performance
2. **Sử dụng LIMIT**: Thêm `LIMIT` khi test queries để tránh query quá lâu
3. **Kiểm tra NULL**: Sử dụng `OPTIONAL MATCH` và kiểm tra `IS NOT NULL` khi cần
4. **Index**: Đảm bảo có index trên `id` và `name` cho các node types
5. **EXPLAIN/PROFILE**: Dùng `EXPLAIN` hoặc `PROFILE` để tối ưu queries phức tạp

### Ví dụ sử dụng EXPLAIN

```cypher
EXPLAIN MATCH (dis:Disease {id: '5044'})-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
RETURN p.name, count(r);
```

---

## Troubleshooting - Xử lý sự cố

### Vấn đề: Query không trả về kết quả mặc dù có relationship trên graph

**Nguyên nhân phổ biến:**

1. **Nhầm lẫn giữa Internal Neo4j ID và Property ID**
   - Internal ID: Số tự động của Neo4j (ví dụ: 3573, 3753)
   - Property ID: Giá trị trong property `id` của node (thường là string, ví dụ: '5044', '13924_12592_...')

**Giải pháp:**

```cypher
// Bước 1: Kiểm tra node có internal ID = 3573
MATCH (dis:Disease)
WHERE id(dis) = 3573
RETURN dis.id as property_id, 
       dis.name as disease_name,
       id(dis) as internal_id,
       labels(dis) as labels;

// Bước 2a: Nếu muốn dùng internal ID
MATCH (dis:Disease)-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
WHERE id(dis) = 3573
RETURN dis.id as disease_id,
       dis.name as disease_name,
       p.id as phenotype_id,
       p.name as phenotype_name,
       r.display_relation as display_relation
ORDER BY p.name;

// Bước 2b: Nếu muốn dùng property ID (sau khi biết property_id từ bước 1)
MATCH (dis:Disease {id: $property_id})-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
RETURN dis.id as disease_id,
       dis.name as disease_name,
       p.id as phenotype_id,
       p.name as phenotype_name,
       r.display_relation as display_relation
ORDER BY p.name;
```

2. **Sai label cho Phenotype**
   - Label đúng: `Effect_phenotype` (không phải `Phenotype`)

**Giải pháp:**

```cypher
// Kiểm tra label thực tế của nodes
MATCH (n)
WHERE n.type CONTAINS 'phenotype' OR n.type CONTAINS 'effect'
RETURN DISTINCT labels(n) as node_labels, n.type as node_type
LIMIT 10;

// Query đúng với label Effect_phenotype
MATCH (dis:Disease)-[r:DISEASE_PHENOTYPE_POSITIVE]->(p:Effect_phenotype)
WHERE id(dis) = 3573
RETURN dis.name, p.name, r.display_relation;
```

3. **Property ID là string, không phải số**

**Giải pháp:**

```cypher
// SAI: {id: 3573} - tìm số
// ĐÚNG: {id: '3573'} - tìm string (nếu property id là string)

// Kiểm tra kiểu dữ liệu của property id
MATCH (dis:Disease)
WHERE id(dis) = 3573
RETURN dis.id, 
       typeof(dis.id) as id_type,
       dis.name;
```

4. **Kiểm tra relationship type có đúng không**

```cypher
// Kiểm tra các relationship types thực tế
MATCH (dis:Disease)-[r]->(p:Effect_phenotype)
WHERE id(dis) = 3573
RETURN DISTINCT type(r) as relationship_type, count(*) as count;

// Kiểm tra tất cả relationships từ disease
MATCH (dis:Disease)-[r]->()
WHERE id(dis) = 3573
RETURN DISTINCT type(r) as relationship_type, labels(endNode(r)) as target_label, count(*) as count;
```

### Query debug tổng hợp

```cypher
// Query để debug hoàn chỉnh: Kiểm tra node, labels, relationships
MATCH (dis:Disease)
WHERE id(dis) = 3573
OPTIONAL MATCH (dis)-[r]->(target)
RETURN dis.id as disease_property_id,
       dis.name as disease_name,
       id(dis) as disease_internal_id,
       labels(dis) as disease_labels,
       type(r) as relationship_type,
       labels(target) as target_labels,
       target.name as target_name,
       count(r) as relationship_count
ORDER BY relationship_type;
```

---

## Tài liệu tham khảo

- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [PrimeKG Documentation](https://github.com/gnn4dr/PrimeKG)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)

---

**Last Updated**: 2025-12-02  
**Version**: 1.0



