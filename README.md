# AI Agent Analytics Assistant

An LLM-powered analytics agent that turns natural-language business questions into SQL, runs them against a **PostgreSQL** e-commerce database, and returns formatted results in a React chat UI.

Retrieval-augmented generation (RAG) uses a local **ChromaDB** vector store (schema docs + few-shot query history) so the LLM gets the right tables and examples before writing SQL.

The agent itself is a **LangGraph** state machine. Generation, validation, execution, and
repair are separate nodes, and conditional edges decide what happens next based on whether
the SQL passed validation and whether it actually ran.

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
 ══════════ LangGraph state machine ══════════

                      ┌────────────────┐
                      │  generate_sql  │  Groq writes SQL from the
                      └────────┬───────┘  retrieved context
                               ▼
                      ┌────────────────┐
    ┌────────────────►│  validate_sql  │  privacy guard + SELECT-only
    │             ┌───┤                │  + known tables / columns
    │             │   └────────┬───────┘
    │        fail │            │ pass
    │             ▼            ▼
    │      ┌────────────┐  ┌────────────────┐
    │      │   reject   │  │  execute_sql   │  the only node that
    │      │   (END)    │  │  (PostgreSQL)  │  touches the database
    │      └────────────┘  └───┬────────┬───┘
    │                    error │        │ success
    │                          │        ▼
    │      ┌────────────┐      │   ┌────────────┐
    └──────┤ repair_sql │◄─────┘   │  finalize  │  format rows, leak
           └────────────┘          └────────────┘  scan, Q→SQL → Chroma
        max 3 execution attempts; after
        the third the graph ends with the error
```

### Graph routing

Two conditional edges do all the branching:

**1. After `validate_sql`** — nothing reaches PostgreSQL until validation passes.

| Outcome | Route |
|---------|-------|
| Passes every check | `execute_sql` |
| Fails any check | `reject` → END, with the reason returned to the user |

A rejected request never opens a database connection. The generated SQL is discarded at
this node, so an unsafe or privacy-violating query has no chance to run.

**2. After `execute_sql`** — branch on the driver's response.

| Outcome | Route |
|---------|-------|
| Ran cleanly | `finalize` — format rows, scan for leaked identities, write the Q→SQL pair back to Chroma |
| Failed and attempts used < 3 | `repair_sql` — feed the Postgres error back to the model, then re-enter `validate_sql` |
| Failed on the 3rd attempt | END, returning the last database error |

The retry counter lives in the graph state, so the loop is bounded at **three execution
attempts** total. Repaired SQL is *re-validated* rather than sent straight to the database —
the model rewriting a query cannot smuggle it past the guard.

## Data stores

| Store | Location | Role |
|-------|----------|------|
| **PostgreSQL** | `public` schema | Business data (products, orders, customers, …) |
| **PostgreSQL** | `accounts` schema | Accounts, sessions, per-user question history |
| **ChromaDB** | `.chroma/` | Vector DB: embeddings + document text + metadata |

Both schemas live in the database named by `DATABASE_URL`. Keeping accounts in their own
schema means auth data never mixes with the business dataset the agent queries, and the
agent's connection can be granted read-only access to `public` alone.

Chroma collection `retrieval_docs` schema:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | Document id (`schema::products`, `history::…`) |
| `document` | text | Embedded text (table description or Q→SQL pair) |
| `embedding` | vector | Local `all-MiniLM-L6-v2` embedding (384-dim) |
| `doc_type` | metadata | `schema` or `history` |
| `table` | metadata | Table name (schema docs) |
| `question` | metadata | Natural-language question (history) |
| `sql` | metadata | SQL example (history) |
| `user_id` | metadata | Owning account, or `""` for shared seed examples |

The collection is created with `metadata={"hnsw:space": "cosine"}`, so retrieval runs on
Chroma's built-in **HNSW** index rather than the FAISS `IndexFlatIP` this project started
with. See the vector store notes below for why that swap matters.

## Project structure

```
AI-Agent-Analytics-Assistant/
├── app.py                # Interactive CLI entry point
├── api.py                # FastAPI server for the React frontend
├── auth.py               # Accounts, sessions, per-user question history
├── graph.py              # LangGraph state machine (nodes + conditional edges)
├── sql_agent.py          # Core NL→SQL agent (Groq + validation + execution)
├── context_manager.py    # Retrieval-augmented prompt builder
├── vector_store.py       # ChromaDB vector store + embeddings
├── setup_database.py     # PostgreSQL sample e-commerce database
├── evaluate.py           # Evaluation harness (200+ test queries)
├── frontend/             # React (Vite) chat UI
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

# 3. Start PostgreSQL and create the database
createdb analytics            # or: docker run -d --name analytics-pg \
                              #       -e POSTGRES_PASSWORD=postgres \
                              #       -e POSTGRES_DB=analytics \
                              #       -p 5432:5432 postgres:16

# 4. Configure environment
cp .env.example .env
# Edit .env:
#   GROQ_API_KEY=gsk_...      get a key at https://console.groq.com/keys
#   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/analytics

# 5. Create the schemas, load sample data, build Chroma
python app.py --setup

# 6. Install frontend dependencies
cd frontend && npm install && cd ..
```

`--setup` is idempotent: it creates the `public` and `accounts` schemas, seeds the sample
e-commerce data, and indexes the introspected schema into Chroma.

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

**Production:** [Render (fastest, stable URL)](DEPLOY_RENDER.md) · [Oracle VM (persistent data, free)](DEPLOY_ORACLE.md)

On first visit you create an account (name, email, password) or sign in. Every
question is recorded against the signed-in account.

Signing up also creates a matching **customer** in the business schema — a profile plus
its own orders, items, and reviews — so personal questions work right away:
“How much have I spent?”, “What have I ordered so far?”. The generated history is
seeded from the email address, so an account always gets the same data back.

**What you can ask**

| | Example |
|---|---|
| Your own data | “How much have I spent?”, “Which categories have I never bought from?” |
| Store-wide aggregates | “Top 5 products by revenue”, “How many orders per city?” |
| Refused | “Which customers spent over $500?”, “Show me Alice Smith's orders” |

Other shoppers are private. The agent refuses any query that would surface another
person's name, email, or phone; see the privacy boundary under `sql_agent.py` below.

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
- **Indexing is Chroma's own HNSW index**, configured with `{"hnsw:space": "cosine"}` on the
  collection. An earlier version of this project used a FAISS `IndexFlatIP` — a flat index
  that scored the query against every stored vector and needed manually L2-normalised
  embeddings for inner product to behave like cosine similarity. Chroma replaces both:
  - The HNSW graph is approximate, so search stays sub-linear as history grows instead of
    scanning the whole set on every question
  - `cosine` space is declared once on the collection, so normalisation is handled internally
  - The index persists and is updated in place on `upsert`, so feeding a new Q→SQL pair back
    does not mean rebuilding and re-saving the index the way a flat FAISS file did
  - Metadata filters (`doc_type`, `user_id`) are applied by the same query, which a bare FAISS
    index cannot do — it returns positions, leaving you to keep a parallel id→document map
- Distances come back as cosine distance and are converted to a `1 - distance` similarity
  score for callers
- Indexes **schema descriptions** (introspected from PostgreSQL's `information_schema`) and **query history** (question→SQL pairs)
- History documents carry a `user_id`, so few-shot retrieval only draws on shared seed
  examples plus the asking user's own past questions
- Persists under `.chroma/`; `upsert` keys mean re-running setup refreshes schema docs
  without duplicating them

### Context manager (`context_manager.py`)
- Injects the signed-in user's identity so “I / me / my” resolves to their `customers.email`
- Retrieves top-k relevant schemas and few-shot examples per question
- Always includes the **full foreign-key map**, since top-k retrieval can miss a table
  that is only needed as a join hop
- Prompt rules cover row counts vs. time windows and an anti-join (`NOT EXISTS`) template
- Builds the system prompt with schema context + similar examples
- Feedback loop: successful queries are upserted back into Chroma

### Graph (`graph.py`)
- **LangGraph** `StateGraph` holding the question, generated SQL, attempt count, result,
  and rejection reason
- Nodes: `generate_sql` → `validate_sql` → `execute_sql` → `finalize`, plus `repair_sql`
- `add_conditional_edges` on `validate_sql` routes to `execute_sql` or to `reject`
- `add_conditional_edges` on `execute_sql` routes to `finalize`, to `repair_sql`, or to
  END once the attempt count hits 3
- Because retries are edges rather than nested `try`/`except`, every path is inspectable —
  the state carries which branch was taken and why, which is what the `--verbose` flag prints

### SQL agent (`sql_agent.py`)
- Calls **Groq** with retrieved context to generate SQL, and cleans the output
  (strips markdown fences, etc.)
- **Validation gate** — SQL only reaches PostgreSQL once all of these pass:
  - **Read-only**: a single `SELECT` (or `WITH … SELECT`); `INSERT`, `UPDATE`, `DELETE`,
    `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `COPY`, and stacked statements are rejected
  - **Known objects**: every table and column resolves against the introspected schema, so
    a hallucinated name is caught before the database sees it
  - **Privacy boundary**: a query that surfaces identity columns (`first_name`,
    `last_name`, `email`, `phone`) from `customers` is refused unless it is pinned to the
    signed-in email. Aggregates that don't name individuals still run.
- A failed check ends the request at that node with an explanation — no connection is
  opened and no SQL is executed
- Appends `LIMIT n` when the question names a row count and the model omitted it
- Executes validated SQL against PostgreSQL and returns pandas DataFrames
- Repairs its own SQL by feeding the Postgres error back to the model, bounded at three
  execution attempts; each repair goes back through validation
- Results are scanned so another person's email can never come back in a row
- Feeds successful pairs back into the vector store

### Accounts (`auth.py`)
- Separate `accounts` schema — user data never mixes with the business dataset
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

The `public` schema in PostgreSQL includes:

- **15 categories** across 7 departments
- **~170+ products** with prices and stock levels
- **500 customers** across 24 US cities
- **2,500 orders** with multiple statuses
- **~8,000+ order items** with line totals
- **1,800 product reviews** with 1–5 star ratings

Each account that signs up adds one more customer, plus roughly 7 orders and 5 reviews
of their own.

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Free API key from [Groq Console](https://console.groq.com/keys) |
| `DATABASE_URL` | Yes | PostgreSQL connection string, e.g. `postgresql://postgres:postgres@localhost:5432/analytics` |
