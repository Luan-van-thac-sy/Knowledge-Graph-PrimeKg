# PrimeKG to Neo4j - Drug Recommendation System

This project imports the Precision Medicine Knowledge Graph (PrimeKG) into a Neo4j database for data analysis and drug recommendation.

## Overview

PrimeKG is a comprehensive biomedical knowledge graph that integrates 20 high-quality biomedical resources to describe 17,080 diseases with over 4 million relationships across ten major biological scales.

This project:
1. Downloads and processes PrimeKG data
2. Imports the data into a Neo4j graph database
3. Provides tools for querying and analyzing the data
4. Enables drug recommendation based on disease relationships

## Project Structure

```
primekg-mcp/
├── config/           # Configuration files
├── data/             # Data files (PrimeKG data will be stored here)
├── docs/             # Documentation
├── scripts/          # Utility scripts for data processing
├── src/              # Source code
│   ├── db/           # Database connection and queries
│   ├── etl/          # Data extraction, transformation, loading
│   └── utils/        # Utility functions
└── tests/            # Test files
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Neo4j 5.13.0+

### Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start Neo4j using Docker Compose:
```bash
docker compose up -d
```

4. Load PrimeKG data:
```bash
python src/main.py load --max-rows 10000
```

## Usage

### Loading Data

```bash
# Load all data
python src/main.py load

# Load limited rows (for testing)
python src/main.py load --max-rows 10000
```

### Querying Data

```bash
# Run example queries
python scripts/query_examples.py
```

---

# Drug Recommendation Queries Guide

Tài liệu hướng dẫn sử dụng Cypher queries để truy xuất thông tin drug recommendation từ PrimeKG database trong Neo4j.

## Mục lục

1. [Tổng quan về dữ liệu](#tổng-quan-về-dữ-liệu)
2. [Khám phá cấu trúc dữ liệu](#khám-phá-cấu-trúc-dữ-liệu)
3. [Drug Recommendation Queries](#drug-recommendation-queries)
4. [Thống kê và Metrics](#thống-kê-và-metrics)
5. [Advanced Queries](#advanced-queries)
6. [Sử dụng trong Python](#sử-dụng-trong-python)
7. [Ví dụ thực tế](#ví-dụ-thực-tế)

---

## Tổng quan về dữ liệu

Database PrimeKG chứa:
- **Nodes**: Drugs và Diseases
- **Relationships**: Các mối quan hệ giữa drugs và diseases (treats, off-label use, etc.)
- **Properties**: 
  - Nodes: `id`, `name`, `type`, `source`
  - Relationships: `display_relation`

### Cấu trúc dữ liệu

```
(Drug)-[RELATIONSHIP_TYPE]->(Disease)
```

---

## Khám phá cấu trúc dữ liệu

### 1. Xem tổng quan về nodes

```cypher
// Đếm số lượng nodes theo loại
MATCH (n)
RETURN labels(n) as node_type, count(n) as count
ORDER BY count DESC;
```

### 2. Xem các loại relationships

```cypher
// Đếm số lượng relationships theo loại
MATCH ()-[r]->()
RETURN type(r) as relationship_type, count(r) as count
ORDER BY count DESC;
```

### 3. Xem cấu trúc mẫu

```cypher
// Xem một drug node mẫu
MATCH (d:Drug)
RETURN d LIMIT 1;

// Xem một relationship mẫu
MATCH (d:Drug)-[r]->(dis:Disease)
RETURN d, r, dis LIMIT 1;
```

---

## Drug Recommendation Queries

### 1. Tìm drugs cho một disease cụ thể (theo ID)

```cypher
MATCH (d:Drug)-[r]->(dis:Disease {id: '5044'})
RETURN d.id as drug_id, 
       d.name as drug_name, 
       type(r) as relationship_type,
       r.display_relation as display_relation
ORDER BY d.name;
```

**Kết quả**: Danh sách tất cả drugs có thể điều trị disease với ID '5044'

### 2. Tìm drugs cho một disease (theo tên - tìm kiếm gần đúng)

```cypher
MATCH (d:Drug)-[r]->(dis:Disease)
WHERE dis.name CONTAINS 'diabetes' OR dis.name CONTAINS 'Diabetes'
RETURN dis.name as disease_name,
       dis.id as disease_id,
       d.name as drug_name,
       d.id as drug_id,
       type(r) as relationship_type,
       r.display_relation as display_relation
ORDER BY dis.name, d.name;
```

**Kết quả**: Tất cả drugs liên quan đến diseases có chứa từ "diabetes" trong tên

### 3. Top N drugs được khuyến nghị nhiều nhất cho một disease

```cypher
MATCH (d:Drug)-[r]->(dis:Disease {id: '5044'})
WITH d, count(r) as recommendation_count
RETURN d.id as drug_id,
       d.name as drug_name,
       d.source as drug_source,
       recommendation_count
ORDER BY recommendation_count DESC
LIMIT 10;
```

**Kết quả**: Top 10 drugs có nhiều relationships nhất với disease '5044'

### 4. Tìm diseases cho một drug cụ thể

```cypher
MATCH (d:Drug {id: 'DB00903'})-[r]->(dis:Disease)
RETURN dis.id as disease_id,
       dis.name as disease_name,
       type(r) as relationship_type,
       r.display_relation as display_relation
ORDER BY dis.name;
```

**Kết quả**: Tất cả diseases mà drug 'DB00903' có thể điều trị

### 5. Tìm diseases cho một drug (theo tên)

```cypher
MATCH (d:Drug)-[r]->(dis:Disease)
WHERE d.name CONTAINS 'aspirin' OR d.name CONTAINS 'Aspirin'
RETURN d.name as drug_name,
       d.id as drug_id,
       dis.name as disease_name,
       dis.id as disease_id,
       type(r) as relationship_type
ORDER BY d.name, dis.name;
```

---

## Drug Recommendation với Scoring

### 1. Drug recommendation với điểm số

```cypher
MATCH (d:Drug)-[r]->(dis:Disease)
WITH d, dis, count(r) as relationship_strength
WHERE relationship_strength > 0
RETURN dis.id as disease_id,
       dis.name as disease_name,
       d.id as drug_id,
       d.name as drug_name,
       relationship_strength as recommendation_score
ORDER BY dis.name, recommendation_score DESC;
```

**Kết quả**: Danh sách drug-disease pairs với điểm số recommendation

### 2. Top drugs tốt nhất cho một disease (đa dạng relationships)

```cypher
MATCH (d:Drug)-[r]->(dis:Disease {id: '5044'})
WITH d, collect(DISTINCT type(r)) as relationship_types
RETURN d.id as drug_id,
       d.name as drug_name,
       relationship_types,
       size(relationship_types) as diversity_score
ORDER BY diversity_score DESC, d.name
LIMIT 10;
```

**Kết quả**: Top 10 drugs với nhiều loại relationships nhất (đa dạng hơn = tốt hơn)

---

## Drug Similarity Queries

### 1. Tìm drugs tương tự (dựa trên diseases chung)

```cypher
MATCH (d1:Drug)-[r1]->(dis:Disease)<-[r2]-(d2:Drug)
WHERE d1.id <> d2.id
WITH d1, d2, count(DISTINCT dis) as common_diseases
WHERE common_diseases >= 2
RETURN d1.id as drug1_id,
       d1.name as drug1_name,
       d2.id as drug2_id,
       d2.name as drug2_name,
       common_diseases
ORDER BY common_diseases DESC
LIMIT 20;
```

**Kết quả**: Các cặp drugs tương tự (điều trị ít nhất 2 diseases chung)

### 2. Tìm alternative drugs

```cypher
MATCH (target_drug:Drug {id: 'DB00903'})-[r]->(dis:Disease)<-[r2]-(alternative:Drug)
WHERE target_drug.id <> alternative.id
RETURN dis.name as disease_name,
       alternative.id as alternative_drug_id,
       alternative.name as alternative_drug_name,
       count(*) as shared_diseases
ORDER BY shared_diseases DESC;
```

**Kết quả**: Các drugs thay thế cho drug 'DB00903'

---

## Thống kê và Metrics

### 1. Top 10 drugs được khuyến nghị nhiều nhất

```cypher
MATCH (d:Drug)-[r]->()
WITH d, count(r) as relationship_count
RETURN d.id as drug_id,
       d.name as drug_name,
       d.source as source,
       relationship_count
ORDER BY relationship_count DESC
LIMIT 10;
```

### 2. Top 10 diseases có nhiều drugs điều trị nhất

```cypher
MATCH (d:Drug)-[r]->(dis:Disease)
WITH dis, count(DISTINCT d) as drug_count
RETURN dis.id as disease_id,
       dis.name as disease_name,
       drug_count
ORDER BY drug_count DESC
LIMIT 10;
```

### 3. Phân bố số lượng drugs per disease

```cypher
MATCH (d:Drug)-[r]->(dis:Disease)
WITH dis, count(DISTINCT d) as drug_count
RETURN drug_count,
       count(dis) as number_of_diseases
ORDER BY drug_count;
```

**Kết quả**: Histogram cho biết có bao nhiêu diseases có X drugs

### 4. Thống kê theo relationship types

```cypher
MATCH (d:Drug)-[r]->(dis:Disease)
RETURN type(r) as relationship_type,
       count(r) as count,
       count(DISTINCT d) as unique_drugs,
       count(DISTINCT dis) as unique_diseases
ORDER BY count DESC;
```

---

## Advanced Queries

### 1. Tìm drugs cho multiple diseases

```cypher
MATCH (d:Drug)-[r]->(dis:Disease)
WHERE dis.id IN ['5044', '5391', '5027']
WITH d, collect(DISTINCT dis.name) as treated_diseases, count(DISTINCT dis) as disease_count
WHERE disease_count >= 2
RETURN d.id as drug_id,
       d.name as drug_name,
       treated_diseases,
       disease_count
ORDER BY disease_count DESC;
```

**Kết quả**: Drugs có thể điều trị ít nhất 2 trong số các diseases được chỉ định

### 2. Tìm drugs theo source

```cypher
MATCH (d:Drug)-[r]->(dis:Disease)
WHERE d.source = 'DrugBank'
RETURN d.id as drug_id,
       d.name as drug_name,
       count(DISTINCT dis) as diseases_treated
ORDER BY diseases_treated DESC
LIMIT 20;
```

### 3. Tìm diseases tương tự (có cùng drugs)

```cypher
MATCH (d:Drug)-[r1]->(dis1:Disease)
MATCH (d)-[r2]->(dis2:Disease)
WHERE dis1.id <> dis2.id
WITH dis1, dis2, count(DISTINCT d) as shared_drugs
WHERE shared_drugs >= 3
RETURN dis1.name as disease1,
       dis2.name as disease2,
       shared_drugs
ORDER BY shared_drugs DESC
LIMIT 20;
```

**Kết quả**: Các cặp diseases có ít nhất 3 drugs chung

---

## Sử dụng trong Python

### Kết nối và thực thi queries

```python
from src.db.neo4j_connector import get_connector

# Kết nối database
db = get_connector()
if not db.connect():
    print("Failed to connect to Neo4j")
    exit(1)

# Query 1: Tìm drugs cho một disease
query = """
MATCH (d:Drug)-[r]->(dis:Disease {id: $disease_id})
RETURN d.id as drug_id, 
       d.name as drug_name, 
       type(r) as relationship_type
ORDER BY d.name
"""

result = db.execute_read_query(query, {'disease_id': '5044'})
print(result)

# Query 2: Top drugs
query = """
MATCH (d:Drug)-[r]->()
WITH d, count(r) as relationship_count
RETURN d.id, d.name, relationship_count
ORDER BY relationship_count DESC
LIMIT 10
"""

result = db.execute_read_query(query)
for record in result.get('records', []):
    print(f"Drug: {record.get('d.name')}, Count: {record.get('relationship_count')}")
```

### Hàm tiện ích để lấy drug recommendations

```python
def get_drugs_for_disease(disease_id: str, limit: int = 10):
    """
    Lấy danh sách drugs được khuyến nghị cho một disease
    
    Args:
        disease_id: ID của disease
        limit: Số lượng drugs tối đa
    
    Returns:
        List of drug recommendations
    """
    query = """
    MATCH (d:Drug)-[r]->(dis:Disease {id: $disease_id})
    WITH d, count(r) as recommendation_count
    RETURN d.id as drug_id,
           d.name as drug_name,
           d.source as source,
           recommendation_count
    ORDER BY recommendation_count DESC
    LIMIT $limit
    """
    
    result = db.execute_read_query(query, {
        'disease_id': disease_id,
        'limit': limit
    })
    
    return result.get('records', [])

# Sử dụng
drugs = get_drugs_for_disease('5044', limit=5)
for drug in drugs:
    print(f"{drug.get('drug_name')}: {drug.get('recommendation_count')} relationships")
```

### Hàm tìm diseases cho một drug

```python
def get_diseases_for_drug(drug_id: str):
    """
    Lấy danh sách diseases mà một drug có thể điều trị
    
    Args:
        drug_id: ID của drug
    
    Returns:
        List of diseases
    """
    query = """
    MATCH (d:Drug {id: $drug_id})-[r]->(dis:Disease)
    RETURN dis.id as disease_id,
           dis.name as disease_name,
           type(r) as relationship_type,
           r.display_relation as display_relation
    ORDER BY dis.name
    """
    
    result = db.execute_read_query(query, {'drug_id': drug_id})
    return result.get('records', [])

# Sử dụng
diseases = get_diseases_for_drug('DB00903')
for disease in diseases:
    print(f"{disease.get('disease_name')}: {disease.get('relationship_type')}")
```

---

## Ví dụ thực tế

### Scenario 1: Tìm drugs cho bệnh tiểu đường

```cypher
// Bước 1: Tìm disease ID cho "diabetes"
MATCH (dis:Disease)
WHERE dis.name CONTAINS 'diabetes' OR dis.name CONTAINS 'Diabetes'
RETURN dis.id, dis.name
LIMIT 5;

// Bước 2: Tìm drugs cho disease ID tìm được
MATCH (d:Drug)-[r]->(dis:Disease {id: 'YOUR_DIABETES_ID'})
RETURN d.name as drug_name,
       d.id as drug_id,
       type(r) as relationship_type
ORDER BY d.name;
```

### Scenario 2: So sánh 2 drugs

```cypher
// So sánh 2 drugs dựa trên diseases chung
MATCH (d1:Drug {id: 'DB00903'})-[r1]->(dis:Disease)<-[r2]-(d2:Drug {id: 'DB00887'})
RETURN dis.name as common_disease,
       type(r1) as drug1_relationship,
       type(r2) as drug2_relationship;

// Đếm số diseases chung
MATCH (d1:Drug {id: 'DB00903'})-[r1]->(dis:Disease)<-[r2]-(d2:Drug {id: 'DB00887'})
RETURN count(DISTINCT dis) as common_diseases_count;
```

### Scenario 3: Tìm drug combination (2 drugs điều trị cùng 1 disease)

```cypher
MATCH (d1:Drug)-[r1]->(dis:Disease)<-[r2]-(d2:Drug)
WHERE d1.id <> d2.id
RETURN d1.name as drug1,
       d2.name as drug2,
       dis.name as disease,
       type(r1) as relationship1,
       type(r2) as relationship2
ORDER BY dis.name
LIMIT 20;
```

---

## Validation và Quality Checks

### 1. Kiểm tra drugs không có relationships

```cypher
MATCH (d:Drug)
WHERE NOT (d)-[]->()
RETURN d.id, d.name, d.source;
```

### 2. Kiểm tra diseases không có drugs

```cypher
MATCH (dis:Disease)
WHERE NOT ()-[]->(dis)
RETURN dis.id, dis.name;
```

### 3. Kiểm tra duplicate relationships

```cypher
MATCH (d:Drug)-[r]->(dis:Disease)
WITH d, dis, type(r) as rel_type, count(r) as count
WHERE count > 1
RETURN d.id, d.name, dis.id, dis.name, rel_type, count
ORDER BY count DESC;
```

---

## Export Data cho Machine Learning

### Export drug-disease pairs với features

```cypher
MATCH (d:Drug)-[r]->(dis:Disease)
RETURN d.id as drug_id,
       d.name as drug_name,
       d.source as drug_source,
       dis.id as disease_id,
       dis.name as disease_name,
       type(r) as relationship_type,
       r.display_relation as display_relation
ORDER BY d.name, dis.name
LIMIT 1000;
```

### Export với Python để lưu CSV

```python
import pandas as pd
from src.db.neo4j_connector import get_connector

db = get_connector()
db.connect()

query = """
MATCH (d:Drug)-[r]->(dis:Disease)
RETURN d.id as drug_id,
       d.name as drug_name,
       d.source as drug_source,
       dis.id as disease_id,
       dis.name as disease_name,
       type(r) as relationship_type,
       r.display_relation as display_relation
"""

result = db.execute_read_query(query)
records = result.get('records', [])

# Convert to DataFrame
df = pd.DataFrame([
    {
        'drug_id': r.get('drug_id'),
        'drug_name': r.get('drug_name'),
        'drug_source': r.get('drug_source'),
        'disease_id': r.get('disease_id'),
        'disease_name': r.get('disease_name'),
        'relationship_type': r.get('relationship_type'),
        'display_relation': r.get('display_relation')
    }
    for r in records
])

# Lưu CSV
df.to_csv('drug_disease_pairs.csv', index=False)
print(f"Exported {len(df)} records to drug_disease_pairs.csv")
```

---

## Tips và Best Practices

1. **Sử dụng LIMIT**: Luôn thêm `LIMIT` khi test queries để tránh query quá lâu
2. **Index**: Đảm bảo có index trên `id` và `name` cho performance tốt
3. **Parameters**: Sử dụng parameters (`$variable`) thay vì hardcode values
4. **EXPLAIN**: Dùng `EXPLAIN` để xem query plan trước khi chạy query lớn
5. **PROFILE**: Dùng `PROFILE` để đo performance của query

### Ví dụ sử dụng EXPLAIN

```cypher
EXPLAIN MATCH (d:Drug)-[r]->(dis:Disease {id: '5044'})
RETURN d.name, count(r);
```

---

## Troubleshooting

### Query chạy quá chậm

1. Kiểm tra indexes: `SHOW INDEXES`
2. Sử dụng `EXPLAIN` để xem query plan
3. Thêm `LIMIT` để giảm kết quả
4. Tối ưu query pattern (tránh cartesian products)

### Không tìm thấy kết quả

1. Kiểm tra ID có đúng format không (string vs number)
2. Kiểm tra case sensitivity trong tên
3. Xem sample data: `MATCH (n) RETURN n LIMIT 5`

### Out of Memory

1. Giảm số lượng nodes trong query
2. Sử dụng `LIMIT` và `SKIP` cho pagination
3. Tăng heap size trong Neo4j config

---

## Tài liệu tham khảo

- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [PrimeKG Documentation](https://github.com/gnn4dr/PrimeKG)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)

---

## License

(License information will be added)

---

**Last Updated**: 2025-12-02  
**Version**: 1.0
