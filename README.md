# AI Agent Analytics Assistant

An LLM-powered analytics agent that turns natural-language business questions into SQL, runs them against a local e-commerce SQLite database, and returns formatted results in a React chat UI.

Retrieval-augmented generation (RAG) uses a local **ChromaDB** vector store (schema docs + few-shot query history) so the LLM gets the right tables and examples before writing SQL.

## Architecture

```
User Question (Web UI or CLI)
     │
     ▼
┌─────────────────────────────────┐
│   Context Manager               │
│  ┌────────────┐ ┌─────────────┐ │
│  │ Schema     │ │ Query       │ │
│  │ Retrieval  │ │ History     │ │
│  │ (Chroma)   │ │ (Chroma)    │ │
│  └─────┬──────┘ └──────┬──────┘ │
│        └───────┬───────┘        │
└────────────────┼────────────────┘
                 ▼
         ┌──────────────┐
         │ LLM (Groq)   │
         │ SQL Gen      │
         └──────┬───────┘
                ▼
         ┌──────────────┐
         │ SQLite DB    │
         │ Execute SQL  │
         └──────┬───────┘
                ▼
         Formatted Results
         (+ successful Q→SQL pairs → Chroma)
```

## Data stores

| Store | Path | Role |
|-------|------|------|
| **SQLite** | `business.db` | Business data (products, orders, customers, …) |
| **ChromaDB** | `.chroma/` | Vector DB: embeddings + document text + metadata |

Chroma collection `retrieval_docs` schema:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | Document id (`schema::products`, `history::…`) |
| `document` | text | Embedded text (table description or Q→SQL pair) |
| `embedding` | vector | Local `all-MiniLM-L6-v2` embedding |
| `doc_type` | metadata | `schema` or `history` |
| `table` | metadata | Table name (schema docs) |
| `question` | metadata | Natural-language question (history) |
| `sql` | metadata | SQL example (history) |

## Project structure

```
AI-Agent-Analytics-Assistant/
├── app.py                # Interactive CLI entry point
├── api.py                # FastAPI server for the React frontend
├── auth.py               # Accounts, sessions, per-user question history
├── sql_agent.py          # Core NL→SQL agent (Groq + execution)
├── context_manager.py    # Retrieval-augmented prompt builder
├── vector_store.py       # ChromaDB vector store + embeddings
├── setup_database.py     # SQLite sample e-commerce database
├── evaluate.py           # Evaluation harness (200+ test queries)
├── frontend/             # React (Vite) chat UI
├── business.db           # SQLite DB (created on setup)
├── .chroma/              # Chroma persistence (created on setup)
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Set your Groq API key (free tier)
cp .env.example .env
# Edit .env — get a key at https://console.groq.com/keys
# GROQ_API_KEY=gsk_...

# 4. Initialise SQLite + Chroma
python app.py --setup

# 5. Install frontend dependencies
cd frontend && npm install && cd ..
```

## Usage

### Web UI (React)

Terminal 1 — API:

```bash
source venv/bin/activate
uvicorn api:app --reload --port 8000
```

Terminal 2 — frontend:

```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` to port 8000.

On first visit you create an account (name, email, password) or sign in. Every
question is recorded against the signed-in account.

Signing up also creates a matching **customer** in `business.db` — a profile plus
its own orders, items, and reviews — so personal questions work right away:
“How much have I spent?”, “What have I ordered so far?”. The generated history is
seeded from the email address, so an account always gets the same data back.

**API routes**

All routes except `/api/health` and the auth endpoints require a
`Authorization: Bearer <token>` header.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/signup` | `{ name, email, password }` → token + user |
| `POST` | `/api/auth/login` | `{ email, password }` → token + user |
| `POST` | `/api/auth/logout` | Revoke the current session token |
| `GET` | `/api/auth/me` | Signed-in account |
| `GET` | `/api/health` | Readiness, model, provider (`groq`) |
| `GET` | `/api/examples` | Sample questions for the UI |
| `GET` | `/api/schema` | Table / column metadata for Explore |
| `POST` | `/api/ask` | `{ "question": "..." }` → result rows |
| `GET` | `/api/history` | The signed-in user's past questions |
| `DELETE` | `/api/history` | Clear the signed-in user's history |

### Frontend pages

| Route | Page |
|-------|------|
| `/` | **Ask** — chat and answer tables |
| `/history` | That user's saved question history |
| `/explore` | High-level order-management domain diagram |
| `/about` | How the assistant works |

### Interactive CLI

```bash
source venv/bin/activate
python app.py
```

### Evaluation

```bash
# All 200+ test queries
python evaluate.py

# First 20 queries (quick test)
python app.py --eval 20
```

### Options

```bash
python app.py --model llama-3.1-8b-instant   # faster / smaller Groq model
python app.py --verbose                     # context retrieval debug info
```

Default model: `llama-3.3-70b-versatile` (via Groq’s OpenAI-compatible API).

## Key components

### Vector store (`vector_store.py`)
- Local **ChromaDB** collection `retrieval_docs` (vectors, documents, and metadata together)
- Embeddings via `sentence-transformers/all-MiniLM-L6-v2` (local, no API cost)
- Indexes **schema descriptions** (introspected from SQLite) and **query history** (question→SQL pairs)
- History documents carry a `user_id`, so few-shot retrieval only draws on shared seed
  examples plus the asking user's own past questions
- Persists under `.chroma/`

### Context manager (`context_manager.py`)
- Injects the signed-in user's identity so “I / me / my” resolves to their `customers.email`
- Retrieves top-k relevant schemas and few-shot examples per question
- Builds the system prompt with schema context + similar examples
- Feedback loop: successful queries are upserted back into Chroma

### SQL agent (`sql_agent.py`)
- **Privacy boundary**: a query that surfaces identity columns (`first_name`,
  `last_name`, `email`, `phone`) from `customers` is refused unless it is pinned to the
  signed-in email. Aggregates that don't name individuals still run, and results are
  scanned so another person's email can never come back in a row.
- Repairs its own SQL once by feeding the database error back to the model
- Appends `LIMIT n` when the question names a row count and the model omitted it
- Calls **Groq** with retrieved context to generate SQL
- Cleans LLM output (strips markdown fences, etc.)
- Executes SQL against SQLite and returns pandas DataFrames
- Feeds successful pairs back into the vector store

### Accounts (`auth.py`)
- Separate SQLite file `accounts.db` — user data never mixes with the business dataset
- Passwords hashed with PBKDF2-HMAC-SHA256 (200k iterations, per-user salt)
- Opaque bearer tokens stored server-side in a `sessions` table, so sign-out revokes them
- `query_history` table records each question against its author

### API (`api.py`)
- FastAPI wrapper around `SQLAgent` for the React frontend
- CORS enabled for local Vite (`localhost:5173`)
- Data routes are behind a bearer-token dependency; `/api/ask` passes the user id down to the agent

### Frontend (`frontend/`)
- React + Vite UI gated behind a sign-in / sign-up screen
- Token kept in `localStorage` and sent on every request; account shown in the sidebar
- History page reads that user's questions back from the server

### Evaluation (`evaluate.py`)
- 200+ test queries (aggregation, joins, filters, dates, subqueries)
- Measures execution accuracy and fragment accuracy
- Supports with-retrieval vs without-retrieval comparison

## Sample database

SQLite (`business.db`) includes:

- **15 categories** across 7 departments
- **~170+ products** with prices and stock levels
- **500 customers** across 24 US cities
- **2,500 orders** with multiple statuses
- **~8,000+ order items** with line totals
- **1,800 product reviews** with 1–5 star ratings

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Free API key from [Groq Console](https://console.groq.com/keys) |
