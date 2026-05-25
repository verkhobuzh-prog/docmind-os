# ADR-001: Graph Database Engine для DocMind OS

**Status:** ACCEPTED  
**Date:** 2026-05-25  
**Deciders:** Backend Team  
**Context:** Phase 1 має pgvector (vector RAG). Graph DB потрібен для  
temporal knowledge graph, legal reasoning, provenance chains.

---

## 1. Контекст і проблема

DocMind OS V12.5 потребує Graph DB для:

- Зберігання юридичних сутностей (Person, Org, Agreement, LegalCase, Policy)
- Temporal edges (`valid_from` / `valid_to`) для реконструкції стану на дату
- Cypher-запитів у `GraphReasoningAgent` (вже існує в коді)
- Multi-hop traversal: «хто підписав договір, що замінив Policy X?»

Поточний стан:

- `falkordb/falkordb` присутній у `docker-compose.yml`
- Backend: `app/db/graph.py`, `GraphService`, `GraphReasoningAgent`
- Postgres audit: `semantic_triples` (provenance fallback без FalkorDB)
- Gap (до цього ADR): образ без pinned tag → non-deterministic upgrades

---

## 2. Варіанти розгляду

| # | Option | Статус |
|---|--------|--------|
| 1 | **FalkorDB** | ✅ Обрано |
| 2 | Neo4j Community Edition | Розглянуто |
| 3 | Memgraph | ❌ Відхилено (менша Python-екосистема) |
| 4 | Apache AGE / pgvector-only graph | ❌ Відхилено (SQL-graph, слабкий Cypher, повільний traversal) |

---

## 3. Порівняльна таблиця

| Критерій | FalkorDB | Neo4j Community | Переможець |
|----------|----------|-----------------|------------|
| **Ліцензія** | RSAL v2 | GPL v3 | 🟡 Обидва OK для self-hosted |
| **Ліцензія (SaaS)** | ⚠️ RSAL: заборонено DBaaS | ⚠️ GPL copyleft | 🟡 Рівна небезпека |
| **Internal use** | ✅ | ✅ | = |
| **Redis-сумісність** | ✅ Redis Module (RESP3) | ❌ | **FalkorDB** |
| **Redis Stack інтеграція** | ✅ | ❌ Окремий процес | **FalkorDB** |
| **Temporal edges** | ✅ Properties on edges | ✅ | = |
| **Cypher** | ✅ OpenCypher (subset) | ✅ Full + APOC | Neo4j |
| **APOC / алгоритми** | ⚠️ Базові | ✅ GDS | Neo4j |
| **Python driver** | `falkordb` (pip) | `neo4j` (pip) | = |
| **Async Python** | ✅ `falkordb.asyncio` + `asyncio.to_thread` | ✅ `AsyncGraphDatabase` | = |
| **Docker image** | ~80 MB | ~600 MB (JVM) | **FalkorDB** |
| **RAM idle** | ~50–150 MB | ~512 MB–1 GB | **FalkorDB** |
| **Dev startup** | ~2 s | ~15–30 s | **FalkorDB** |
| **Vector index** | ✅ (Redis Stack) | ✅ Neo4j 5.x | = |
| **Horizontal scale (Community)** | ❌ Single node | ❌ Single node | = |
| **Enterprise prod** | FalkorDB Cloud / self-hosted | Neo4j Enterprise ($$$) | **FalkorDB** |
| **Вже в коді** | ✅ Cypher agent, GraphService | ❌ Рефакторинг | **FalkorDB** |

---

## 4. Детальний аналіз критеріїв

### 4.1 Ліцензія

**FalkorDB** — Redis Source Available License v2 (RSAL):

- ✅ Безкоштовно для internal use, research, development
- ✅ Self-hosted production — OK
- ⚠️ Заборонено: продавати FalkorDB як окремий cloud database service
- DocMind OS використовує FalkorDB як **компонент**, не перепродає DB → **SAFE**

**Neo4j Community** — GPL v3:

- ✅ Безкоштовно для internal + self-hosted SaaS (no binary distribution)
- ⚠️ Enterprise features (clustering, RBAC) — платні
- Рефакторинг усіх Cypher-запитів + новий operational stack

### 4.2 Redis-сумісність

FalkorDB запускається як **Redis Module** (протокол RESP3, `redis-cli ping`).

**Поточна конфігурація (Phase 1–3):**

- App Redis (cache, rate-limit, queue) — `:6379`
- FalkorDB graph — **окремий інстанс** `:6380` (ізоляція від app cache)
- Перевага: graph не конкурує з eviction policy / TTL cache-ключів

**Опція консолідації через Redis Stack (Phase 4+):**

Якщо об'єднати cache + graph в `redis/redis-stack` або `falkordb/falkordb` як єдиний сервіс:

- Один порт (`6379`) для cache + graph
- Спільна Redis persistence (AOF/RDB)
- Можна query graph і cache в одній транзакції
- Менший Docker footprint

Це **не** обов'язково для Phase 1–3; окремий FalkorDB-контейнер простіший для dev і debugging.

### 4.3 Temporal Edges

Обидві БД підтримують temporal через **properties на ребрах**:

```cypher
-- FalkorDB / Neo4j Cypher (однаковий синтаксис)
CREATE (a)-[:SIGNED_BY {
  valid_from: date('2024-01-01'),
  valid_to: date('2025-12-31'),
  confidence: 0.95
}]->(b)
```

Немає нативного bitemporal типу — реалізуємо через властивості (достатньо для Phase 1–2).

### 4.4 Python Driver

```python
# FalkorDB
from falkordb import FalkorDB
db = FalkorDB(host='localhost', port=6380)
graph = db.select_graph('legal_graph')
result = graph.query("MATCH (n:Agreement) RETURN n LIMIT 10")

# Async
from falkordb.asyncio import FalkorDB as AsyncFalkorDB
db = await AsyncFalkorDB.from_url("redis://localhost:6380")
```

```python
# Neo4j
from neo4j import AsyncGraphDatabase
driver = AsyncGraphDatabase.driver("bolt://localhost:7687",
                                    auth=("neo4j", "password"))
async with driver.session() as session:
    result = await session.run("MATCH (n:Agreement) RETURN n LIMIT 10")
```

Обидва — async-ready, офіційно підтримувані. DocMind backend використовує `app/db/graph.py` (FalkorDB sync + `asyncio.to_thread`).

### 4.5 Docker Footprint

| Метрика | FalkorDB (redis-stack) | FalkorDB only (dev) | Neo4j Community |
|---------|------------------------|---------------------|-----------------|
| Image size | ~550 MB (redis-stack) | ~80 MB | ~650 MB |
| RAM idle | ~80–150 MB | ~80–150 MB | ~512 MB (JVM) |
| CPU startup | <2 сек | <2 сек | 15–30 сек |
| Порти | 6379 (Redis protocol) | 6379 → map `:6380` | 7474 + 7687 |
| Volumes needed | redis data dir | redis data dir | data + logs + conf |
| Healthcheck | `redis-cli ping` | `redis-cli ping` | HTTP readiness |

**Поточний dev compose:** окремий `falkordb/falkordb:v4.18.6` на `:6380`, limit 128–256 MB RAM достатньо.

### 4.6 Існуючий код

| Модуль | Роль |
|--------|------|
| `app/db/graph.py` | FalkorDB client, `init_graph()`, `ping_graph()` |
| `app/services/graph_service.py` | Upsert triples, entity search |
| `app/agents/graph_reasoning_agent.py` | Cypher reasoning, risk analysis |
| `app/knowledge/ontology.py` | Entity/relation types |
| `semantic_triples` (Postgres) | Audit trail коли graph недоступний |

OpenCypher subset FalkorDB покриває поточні запити проєкту (1–3 hop traversal, temporal filters).  
APOC-алгоритми (PageRank, community detection) — **не потрібні у Phase 2–3**.

---

## 5. Рішення

### ✅ ВИБІР: FalkorDB

**Обрано:** `falkordb/falkordb:v4.18.6` (pinned у `docker-compose.yml`; не `latest`)

**Причини (ranked):**

1. **Вже в кодовій базі** — `GraphReasoningAgent` використовує FalkorDB Cypher. Зміна = повний рефакторинг.
2. **Redis-нативність** — один сервіс замість двох (опційно через Stack), менший DevOps overhead у dev.
3. **Docker footprint** — критично для локального dev (~8× менше RAM vs Neo4j JVM).
4. **Ліцензія** — RSAL безпечний для нашого use case (internal SaaS, не перепродаємо DB).
5. **Достатній Cypher** — наші запити (1–3 hop traversal, temporal filters) не потребують APOC.

**Dual persistence:** FalkorDB (query) + Postgres `semantic_triples` (audit / fallback).

**Коли переглянути рішення (trigger conditions):**

- Потреба в Graph Data Science алгоритмах (centrality, community detection) → Neo4j GDS
- Потреба в кластеризації / replication → Neo4j Enterprise або Memgraph
- FalkorDB RSAL стає несумісним з бізнес-моделлю → міграція на Neo4j

**Міграційний шлях (якщо знадобиться):**

OpenCypher сумісний між FalkorDB і Neo4j. Schema + queries переносяться з мінімальними змінами (~90% сумісність).

---

## 6. Наслідки

**Позитивні:**

- Нульовий рефакторинг `GraphReasoningAgent`
- Dev environment легший на ~400 MB RAM vs Neo4j
- Можна об'єднати Redis + FalkorDB в redis-stack (опційно, Phase 4+)
- Healthcheck + pinned image → reproducible Docker dev
- Temporal properties на edges підтримуються native

**Негативні / ризики:**

- FalkorDB OpenCypher — підмножина, немає APOC → складні алгоритми вручну
- RSAL ліцензія потребує review при зміні бізнес-моделі (OEM / white-label)
- Менша спільнота vs Neo4j
- Single-node Community — horizontal sharding потребує FalkorDB Cloud або redesign
- Service role backend обходить Postgres RLS — graph isolation через app-layer filters

**Нейтральні:**

- `GRAPH_DB_ENABLED=false` за замовчуванням — graph optional у dev без FalkorDB
- Postgres `semantic_triples` залишається source of truth для provenance audit

**Дії:**

- [x] Зафіксувати версію: `falkordb/falkordb:v4.18.6` (не `latest`)
- [x] Додати healthcheck у docker-compose
- [x] Додати `GRAPH_DB_HOST` / `GRAPH_DB_PORT` до `.env.example`
- [ ] Написати migration script для graph schema (Task B)
- [ ] CI smoke: `ping_graph()` коли `GRAPH_DB_ENABLED=true`
- [ ] Temporal edge schema в ontology

---

## 7. Action items (implementation)

| # | Task | Status |
|---|------|--------|
| 1 | Pin Docker image: `falkordb/falkordb:v4.18.6` | ✅ |
| 2 | Healthcheck `redis-cli ping` у compose | ✅ |
| 3 | Document `GRAPH_DB_HOST`, `GRAPH_DB_PORT`, `GRAPH_DB_URL` у `.env.example` | ✅ |
| 4 | ADR-001 цей документ | ✅ |
| 5 | Graph schema migration script (Task B) | 🔲 Phase 3 |
| 6 | CI smoke: `ping_graph()` коли `GRAPH_DB_ENABLED=true` | 🔲 Phase 3 |
| 7 | Temporal edge schema в ontology | 🔲 Phase 3 |

---

## 8. Конфігурація (reference)

```env
# .env
GRAPH_DB_ENABLED=true
GRAPH_DB_HOST=localhost
GRAPH_DB_PORT=6380
GRAPH_DB_URL=redis://localhost:6380
GRAPH_DB_NAME=docmind_knowledge
```

```yaml
# docker-compose.yml (excerpt)
falkordb:
  image: falkordb/falkordb:v4.18.6
  ports:
    - "6380:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "-p", "6379", "ping"]
```

---

## 9. Related documents

- [03-data-model.md](../architecture/03-data-model.md) — ERD, `semantic_triples`
- [01-c4-architecture.md](../architecture/01-c4-architecture.md) — FalkorDB container
- `backend/app/agents/graph_reasoning_agent.py` — Cypher reasoning
- `backend/app/db/graph.py` — client wrapper

---

## 10. Revision history

| Date | Change |
|------|--------|
| 2026-05-25 | ACCEPTED — FalkorDB v4.18.6, ADR created |
| 2026-05-25 | Expanded §4.2–4.6, ranked decision rationale, action checklist |
