# Паспорт розробника — Doc-Hub

| Поле | Значення |
|------|----------|
| **Проект** | Doc-Hub (DocumentOS) |
| **Версія** | 0.1.0 (Phase 1 MVP) |
| **Аудиторія** | Backend / Full-stack розробники |
| **Пов’язаний документ** | [ARCHITECTURAL_PASSPORT.md](./ARCHITECTURAL_PASSPORT.md) |

---

## 1. Швидкий старт (15 хвилин)

### 1.1 Вимоги

| Інструмент | Версія |
|------------|--------|
| Python | 3.12+ |
| Docker + Docker Compose | остання stable |
| Git | 2.x |
| (опційно) Node.js | 20+ — для frontend |

### 1.2 Клонування та налаштування

```bash
git clone https://github.com/verkhobuzh-prog/doc-hub.git
cd doc-hub
cp .env.example .env
```

Заповніть `.env` (мінімум для повного flow):

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
OPENAI_API_KEY=sk-...
```

### 1.3 Запуск (Docker — рекомендовано)

```bash
docker compose up --build backend postgres redis
```

| URL | Призначення |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Health check |
| localhost:5432 | PostgreSQL (dochub/dochub) |
| localhost:6379 | Redis |

### 1.4 Локальний запуск (без Docker)

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> Запускайте **з каталогу `backend/`**, щоб пакет `app` коректно імпортувався.

### 1.5 Перевірка

```bash
cd backend
pytest -v

curl http://localhost:8000/health
```

Очікування: **9 passed**, health `status: ok` або `degraded`.

---

## 2. Структура проекту (де що лежить)

```
doc-hub/
├── backend/                         # ← основна робота Phase 1
│   ├── app/
│   │   ├── main.py                  # FastAPI factory, lifespan, /health
│   │   ├── core/                    # config, security, logging, exceptions
│   │   ├── db/                      # supabase, postgres, redis
│   │   ├── api/v1/endpoints/        # HTTP handlers (тонкі!)
│   │   ├── services/                # бізнес-логіка
│   │   ├── schemas/                 # Pydantic request/response
│   │   ├── utils/                   # parsers, chunking, retrieval, guardrails
│   │   └── middleware/              # request ID
│   ├── tests/                       # pytest
│   ├── requirements.txt
│   └── requirements-dev.txt
├── infra/supabase/migrations/       # SQL — застосовуються при старті postgres
├── frontend/                        # React scaffold (Phase 2)
├── docs/                            # документація
├── docker-compose.yml
└── .env.example
```

### Правило шарів

```
endpoints → services → db / utils
```

**Не робіть:** SQL/Supabase виклики безпосередньо в `endpoints/`.

---

## 3. Як додати нову фічу (чеклист)

1. **Schema** — `app/schemas/your_feature.py` (Pydantic models)
2. **Service** — `app/services/your_service.py` (логіка)
3. **Endpoint** — `app/api/v1/endpoints/your_feature.py` (router)
4. **Router** — підключити в `app/api/v1/router.py`
5. **Migration** — `infra/supabase/migrations/00X_*.sql` (якщо потрібна БД)
6. **Test** — `backend/tests/test_your_feature.py`
7. **Docs** — оновити README + паспорт (за потреби)

### Приклад: новий endpoint

```python
# app/api/v1/endpoints/example.py
from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.security import get_current_user

router = APIRouter()

@router.get("/hello")
async def hello(current_user: Annotated[dict, Depends(get_current_user)]):
    return {"user_id": current_user["id"]}
```

```python
# app/api/v1/router.py
from app.api.v1.endpoints import example
api_router.include_router(example.router, prefix="/example", tags=["example"])
```

---

## 4. API — довідник для розробника

### 4.1 Ендпоінти Phase 1

| Method | Path | Auth | Що робить |
|--------|------|------|-----------|
| GET | `/health` | — | Статус сервісу |
| GET | `/api/v1/auth/me` | JWT | Профіль користувача |
| POST | `/api/v1/documents/upload` | JWT | Upload + auto-ingest |
| GET | `/api/v1/documents` | JWT | Список документів |
| GET | `/api/v1/documents/{id}` | JWT | Один документ |
| POST | `/api/v1/documents/{id}/ingest` | JWT | Parse → chunk → embed |
| POST | `/api/v1/chat` | JWT | RAG Q&A |

### 4.2 Авторизація

Усі захищені маршрути вимагають заголовок:

```http
Authorization: Bearer <SUPABASE_JWT>
```

Отримати JWT:
- Supabase Dashboard → Authentication → Users → test user
- Або через Supabase client SDK на frontend

**Локальна розробка без JWT** (тільки dev):

```env
ENVIRONMENT=development
AUTH_DISABLED=true
```

> ⚠️ Ніколи не вмикайте `AUTH_DISABLED` у production.

**Org scope (optional):**

```http
X-Org-ID: <uuid-organization>
```

### 4.3 Приклади curl

**Upload:**

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer $JWT" \
  -F "file=@./sample.pdf"
```

**Ingest (sync, для дебагу):**

```bash
curl -X POST "http://localhost:8000/api/v1/documents/{DOC_ID}/ingest?sync=true" \
  -H "Authorization: Bearer $JWT"
```

**Chat:**

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?", "top_k": 8}'
```

**Chat (streaming):**

```bash
curl -N -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize", "stream": true}'
```

---

## 5. Змінні оточення

Повний список: [`.env.example`](../.env.example)

| Змінна | Обов’язкова | Опис |
|--------|-------------|------|
| `SUPABASE_URL` | Так* | URL проекту Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Так* | Server-side key (не в frontend!) |
| `OPENAI_API_KEY` | Для AI | Embeddings + chat |
| `DATABASE_URL` | Docker | `postgresql://dochub:dochub@localhost:5432/dochub` |
| `REDIS_URL` | Docker | `redis://localhost:6379/0` |
| `AUTH_DISABLED` | Ні | `true` — dev без JWT |
| `INGESTION_AUTO_START` | Ні | `true` — ingest після upload |
| `RAG_TOP_K` | Ні | Кількість chunks для RAG (default 8) |

\* Без Supabase: upload/ingest повернуть 503; тести працюють з моками.

---

## 6. База даних та міграції

### 6.1 Міграції

| Файл | Зміст |
|------|-------|
| `001_documents.sql` | Таблиця `documents` + RLS |
| `002_document_chunks.sql` | `document_chunks`, orgs stub, AI logs stub |
| `003_knowledge_graph_metadata.sql` | `semantic_triples` (graph provenance) |
| `004_profiles.sql` | User profiles & subjects |
| `005_pilot_invites_and_catalog.sql` | Invite codes, members, catalog fields |

**Docker:** міграції застосовуються автоматично при першому старті `postgres`.

**Supabase Cloud:** виконайте SQL вручну в SQL Editor або через CLI.

### 6.2 Supabase Storage

1. Створіть bucket **`documents`** (private)
2. Policies: доступ користувача до `{user_id}/*`

Шлях файлу в Storage:

```
{user_id}/{document_id}/{filename}
```

### 6.3 Корисні SQL-запити (dev)

```sql
-- Статуси документів
SELECT id, filename, status, created_at FROM documents WHERE deleted_at IS NULL;

-- Кількість chunks
SELECT document_id, COUNT(*) FROM document_chunks GROUP BY document_id;

-- Chunks без embedding
SELECT COUNT(*) FROM document_chunks WHERE embedding IS NULL;
```

---

## 7. Пайплайни (як це працює в коді)

### 7.1 Upload → Ingest

```
documents.py (upload)
  → DocumentService.upload_document()
    → supabase.upload_file()
    → INSERT documents (status=uploaded)
  → BackgroundTasks → IngestionService.start_ingestion()
```

### 7.2 Ingestion

```
ingestion_service.py
  → status=parsing
  → download_file() from Storage
  → parsers.parse_document()      # PDF/TXT/MD/Excel
  → chunking.chunk_text()         # tiktoken
  → embeddings.embed_texts()    # OpenAI
  → INSERT document_chunks
  → status=indexed | failed
```

### 7.3 RAG Chat

```
rag_service.py
  → guardrails.is_query_allowed()
  → retrieval.get_relevant_chunks()   # hybrid search
  → compress_context()
  → OpenAI chat.completions
  → extract citations [1], [2]
```

---

## 8. Тестування

### 8.1 Запуск

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
pytest -v tests/test_chat.py -k guardrails   # один файл/тест
```

### 8.2 Структура тестів

| Файл | Що перевіряє |
|------|--------------|
| `test_health.py` | GET /health |
| `test_auth.py` | 401 без JWT, /auth/me з mock user |
| `test_documents.py` | upload, list, ingest |
| `test_chat.py` | chat + guardrails unit |

### 8.3 Фікстури (`conftest.py`)

- `client` — без авторизації
- `auth_client` — mock `get_current_user`
- `mock_services` — мок Document/Ingestion/RAG (без Supabase/OpenAI)
- `disable_external_startup` — без реальних DB при старті

### 8.4 Додати тест

```python
def test_my_feature(auth_client):
    response = auth_client.get("/api/v1/my-endpoint")
    assert response.status_code == 200
```

---

## 9. Конвенції коду

### 9.1 Python / FastAPI

| Правило | Приклад |
|---------|---------|
| Async endpoints | `async def get_items():` |
| Type hints | `user_id: str`, `UUID` |
| Pydantic schemas | окремо від ORM/dict |
| Config | тільки через `settings` з `core/config.py` |
| Supabase sync calls | через `run_supabase()` або `asyncio.to_thread` |
| Логи | `get_logger(__name__)` з `core/logging.py` |

### 9.2 Іменування

| Елемент | Конвенція |
|---------|-----------|
| Файли | `snake_case.py` |
| Routers | `documents_router`, `chat_router` |
| Services | `DocumentService`, `RAGService` |
| Tables | `documents`, `document_chunks` |
| API prefix | `/api/v1/` |

### 9.3 Git

```bash
# Гілки
feature/phase2-organizations
fix/upload-mime-validation

# Commits (conventional)
feat(documents): add DOCX parser
fix(rag): handle empty retrieval
test(chat): add streaming test
docs: update developer passport
```

**Не комітити:** `.env`, `venv/`, `__pycache__/`, secrets.

---

## 10. Дебаг та типові проблеми

### 10.1 Логи

```env
LOG_LEVEL=DEBUG
LOG_JSON=false   # читабельніший формат локально
```

Кожен запит має `X-Request-ID` у відповіді — шукайте в логах.

### 10.2 Типові помилки

| Симптом | Причина | Рішення |
|---------|---------|---------|
| `503 Storage service is not configured` | Немає Supabase keys | Заповніть `.env` |
| `401 Not authenticated` | Немає/прострочений JWT | Bearer token або `AUTH_DISABLED=true` |
| `No indexed documents` | Ingest не завершився | POST `.../ingest?sync=true`, перевірте `status` |
| Chunks без embedding | Немає `OPENAI_API_KEY` | Додайте ключ, re-ingest |
| pytest зависає | Lifespan + real DB | Використовуйте `conftest.py` (вже налаштовано) |
| Import `app` failed | Не той cwd | `cd backend` перед uvicorn |

### 10.3 Swagger

http://localhost:8000/docs → **Authorize** → вставте `Bearer <jwt>` (без слова Bearer у полі, якщо UI додає сам).

### 10.4 Перевірка hybrid search

```bash
# PostgreSQL має бути доступний
docker compose ps postgres

# Перевірка pgvector
docker exec -it dochub-postgres psql -U dochub -d dochub -c "\dx"
```

---

## 11. Supabase — налаштування для нового розробника

1. Створіть проект на [supabase.com](https://supabase.com)
2. **Settings → API** — скопіюйте URL, anon key, service_role key
3. **SQL Editor** — виконайте міграції `001`–`005` по порядку (див. §6.1)
4. **Storage** — bucket `documents` + policies
5. **Authentication** — увімкніть Email provider, створіть test user
6. Отримайте JWT через Sign In (або API)

---

## 12. Frontend (Phase 2 — зараз scaffold)

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

Поки UI не підключений до API — використовуйте Swagger/curl.

---

## 13. Корисні команди (шпаргалка)

```bash
# Docker
docker compose up --build backend postgres redis
docker compose logs -f backend
docker compose down -v          # ⚠️ видалить volumes

# Backend
cd backend && uvicorn app.main:app --reload --port 8000
cd backend && pytest -v --tb=short
cd backend && ruff check app    # якщо встановлено

# Git
git status
git checkout -b feature/my-feature
```

---

## 14. Документація проекту

| Документ | Для кого |
|----------|----------|
| [DEVELOPER_PASSPORT.md](./DEVELOPER_PASSPORT.md) | **Ви тут** — онбординг розробника |
| [ARCHITECTURAL_PASSPORT.md](./ARCHITECTURAL_PASSPORT.md) | Архітектура, C4, ризики |
| [PHASE1_COMPLETION.md](./PHASE1_COMPLETION.md) | Що зроблено в Phase 1 |
| [architecture/README.md](./architecture/README.md) | Детальна архітектура |
| [CHANGELOG.md](../CHANGELOG.md) | Історія змін |

---

## 15. Phase 2 — куди дивитись далі

| Задача | Де почати |
|--------|-----------|
| React UI | `frontend/src/` |
| Organizations | `002_document_chunks.sql`, `schemas/` |
| Temporal workers | `app/workflows/` |
| Rate limiting | `db/redis.py`, middleware |
| Cohere rerank | `utils/retrieval.py` |

---

## 16. Контакти та ескалація

| Питання | Куди |
|---------|------|
| Архітектура | [ARCHITECTURAL_PASSPORT.md](./ARCHITECTURAL_PASSPORT.md) |
| API контракт | Swagger `/docs` |
| Баги Phase 1 | GitHub Issues репозиторію |
| Security | Не публікувати `SERVICE_ROLE_KEY` / `OPENAI_API_KEY` |

---

*Версія паспорта: 1.0 | Phase 1 MVP | Оновлюйте при зміні структури API або онбордингу.*
