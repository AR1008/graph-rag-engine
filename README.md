# Graph-Based Knowledge RAG Engine

A production-grade knowledge graph + RAG system that ingests live financial news, extracts entities and relationships using Flair NER + Wikidata disambiguation, and answers questions through dual-LLM verification (local Llama 3.1 + Gemini). Fully containerized with Docker Compose, with a perpetual background ingestion service that learns from user queries.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     INGESTION PIPELINE                          │
│  NewsAPI → spaCy/Flair NER → Wikidata Entity Linking → Store   │
└───────────────────┬─────────────────────────┬───────────────────┘
                    │                         │
              ┌─────▼─────┐           ┌───────▼──────┐
              │   Neo4j   │           │   ChromaDB   │
              │  (Graph)  │           │  (Vectors)   │
              └─────┬─────┘           └───────┬──────┘
                    │                         │
              ┌─────▼─────────────────────────▼──────┐
              │         Hybrid Retriever              │
              │  Graph traversal + Semantic search    │
              └─────────────────────┬────────────────┘
                                    │
              ┌─────────────────────▼────────────────┐
              │           Dual LLM Layer             │
              │  Llama 3.1 (local) → Gemini (verify) │
              └─────────────────────┬────────────────┘
                                    │
              ┌─────────────────────▼────────────────┐
              │        Streamlit Dashboard           │
              │  Chat UI + Graph Explorer + Memory   │
              └──────────────────────────────────────┘
```

### Why Graph RAG over standard RAG

Standard RAG uses vector similarity alone — it finds text that *sounds* similar to your query but can't answer multi-hop questions like "which companies compete with the CEO's former employer." Graph RAG adds a typed knowledge graph (Company → COMPETITOR_OF → Company, Person → CEO_OF → Company) enabling relationship traversal across multiple hops. The hybrid retriever combines both: vector search for semantic relevance, graph traversal for connected entity context.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Knowledge Graph | Neo4j | Industry-standard graph DB, Cypher query language |
| Vector Store | ChromaDB (persistent) | Local-first, production-ready, no external dependency |
| Entity Extraction | Flair NER (`ner` model) | Contextual string embeddings, significantly more accurate than spaCy small model on financial text |
| Entity Disambiguation | Wikidata API + disk cache | Dynamic lookup vs. static gazetteer — handles ambiguous proper nouns (e.g., city names tagged as ORG) without hardcoding |
| Embeddings | `all-mpnet-base-v2` | 768-dimensional sentence embeddings, best quality/speed tradeoff for financial text |
| Local LLM | Llama 3.1 8B via Ollama | Private, free, zero network latency, runs on Apple Silicon |
| Cloud LLM | Gemini Flash | Verification/correction layer for Llama's outputs |
| News Source | NewsAPI | Structured JSON with real article content, no redirect-URL scraping issues |
| Frontend | Streamlit | Python-native, multi-page, chat-style interface |
| Scheduling | APScheduler (BlockingScheduler) | Production-grade Python scheduler, 6-hour ingestion cycles |
| Containerization | Docker Compose | Three-service orchestration: Neo4j + Streamlit app + background ingestion |

---

## Key Design Decisions

**Flair over spaCy for entity extraction.** spaCy's `en_core_web_sm` uses statistical token-level features heavily dependent on capitalization, causing frequent misclassifications in financial news (e.g., stock prices tagged as ORG). Flair's contextual string embeddings look at the full sentence context, giving meaningfully better precision on financial entity names — at the cost of slower inference, which is acceptable in the background ingestion service but would be too slow at query time. Query-time entity extraction (in `hybrid_retriever.py`) still uses spaCy for speed.

**Wikidata disambiguation over a static gazetteer.** A hardcoded list of known locations solves a specific problem for a specific week. Wikidata's knowledge base has P31 ("instance of") properties for millions of entities, resolving ambiguous proper nouns to structured categories (LOCATION, ORGANIZATION, PERSON) that generalize. The two-call lookup (search → claims) with a disk-persisted JSON cache (`entity_cache.json`) makes this practical: first lookup is slow (~400ms), every subsequent lookup across the entire project lifetime is a fast local read. Cache survives Docker restarts via a bind-mounted volume.

**Dynamic topics from conversation history.** The background ingestion service doesn't monitor a hardcoded list of companies (except as a cold-start fallback). It reads from `conversation_memory` — ChromaDB's record of every question a user has asked — and uses those queries as the next cycle's NewsAPI search terms. The system genuinely learns what its users care about and builds knowledge accordingly.

**Two-phase entity resolution in relationship extraction.** Running Wikidata on every org candidate in every sentence independently would be wasteful. Instead: Flair runs once per sentence (stored in `sentence_spans`), unique org names are collected into a `set()` for deduplication across the whole article, then `lookup_entity_type()` runs once per unique name, and `confirmed_orgs` is reused across all sentences. Dramatically fewer API calls per article.

---

## Project Structure

```
graph-rag-engine/
├── app.py                          # Streamlit entry point, multi-page navigation
├── pages/
│   ├── 1_Query.py                  # Chat-style query interface
│   ├── 2_Graph_Explorer.py         # Interactive pyvis graph visualization
│   └── 3_Memory.py                 # Short-term + long-term memory viewer
├── src/
│   ├── __init__.py                 # Central config loader (.env → env vars)
│   ├── pipeline.py                 # Query orchestration: retrieval → LLM → memory
│   ├── background_ingestion.py     # Perpetual APScheduler service
│   ├── ingestion/
│   │   ├── loader.py               # NewsAPI fetching, HTML cleaning
│   │   ├── extractor.py            # Flair NER + Wikidata-filtered relationship extraction
│   │   └── entity_linker.py        # Wikidata P31 lookup with disk-persisted cache
│   ├── graph/
│   │   └── neo4j_client.py         # Neo4j driver, MERGE-based node/relationship creation
│   ├── vector/
│   │   └── chroma_client.py        # ChromaDB persistent client, sentence-level storage
│   ├── retrieval/
│   │   └── hybrid_retriever.py     # Graph traversal + vector search combination
│   └── llm/
│       ├── ollama_client.py        # Llama 3.1 via local Ollama, configurable host
│       └── gemini_client.py        # Gemini Flash verification layer
├── data/
│   ├── chroma/                     # ChromaDB persistent storage (bind-mounted)
│   ├── entity_cache.json           # Wikidata lookup cache (bind-mounted)
│   └── seen_articles.json          # Ingestion deduplication tracker
├── Dockerfile                      # Streamlit app container
├── Dockerfile.ingestion            # Background ingestion container
├── docker-compose.yml              # Three-service orchestration
└── requirements.txt                # Pinned dependencies
```

---

## Setup

### Prerequisites

- Docker Desktop running
- Ollama installed (https://ollama.com/download) with Llama 3.1: `ollama pull llama3.1`
- API keys: NewsAPI (https://newsapi.org) and Gemini (https://aistudio.google.com)

### Environment

Create `.env` in the project root:

```env
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.0-flash
NEWS_API_KEY=your_newsapi_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
OLLAMA_MODEL=llama3.1
```

### Run

```bash
docker-compose up --build
```

Opens at `http://localhost:8501`. Neo4j Browser available at `http://localhost:7474`.

The background ingestion service starts its first cycle immediately on container startup and runs every 6 hours thereafter. Initial cycle takes 3-5 minutes (Flair model load + Wikidata cold cache).

### Run locally (development)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m spacy download en_core_web_sm

# Start Neo4j (required)
docker run --name neo4j-dev -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 -d neo4j:latest

# Run ingestion once to populate the graph
python3 src/background_ingestion.py  # Ctrl+C after first cycle

# Start Streamlit
streamlit run app.py
```

---

## How It Works

### Ingestion

1. `fetch_multiple_queries()` — pulls up to 10 articles per topic from NewsAPI
2. `process_article()` — Flair NER extracts PER/ORG/LOC entities per sentence; spaCy extracts MONEY/DATE
3. `entity_linker.lookup_entity_type()` — Wikidata P31 lookup confirms each ORG (filters location-tagged-as-org false positives like city names); results cached to disk
4. Relationship extraction — two keyword categories:
   - `PERSON_TO_ORG_RELATIONS` (CEO_OF, CHAIRMAN_OF, FOUNDER_OF, LEADS, APPOINTED_AS, STEPPED_DOWN_FROM)
   - `ORG_TO_ORG_RELATIONS` (ACQUIRED, MERGED_WITH, PARTNERED_WITH, INVESTED_IN)
5. `neo4j_client.store_article()` — MERGE-based graph writes (update if exists, create if not)
6. `chroma_client.store_article()` — sentence-level embeddings stored with article metadata
7. `seen_articles.json` — URL-based deduplication prevents reprocessing

### Query

1. `hybrid_retriever.retrieve()`:
   - Vector search: ChromaDB semantic similarity on query
   - Entity extraction: spaCy (fast) + direct graph name-matching (case-insensitive Neo4j scan)
   - Graph traversal: Neo4j relationship lookup for matched entities
2. `pipeline.run()`:
   - Recalls long-term memory (past conversations as additional context)
   - Formats hybrid context with explicit section labels (PAST CONVERSATIONS / THIS SESSION / RELEVANT NEWS / ENTITY RELATIONSHIPS)
   - Llama 3.1 generates grounded answer with explicit "use only this context" instruction
   - Gemini verifies (gracefully degrades to Ollama-only if quota exceeded)
   - Stores Q&A in short-term (list, last 3) and long-term (ChromaDB `conversation_memory`, UUID-keyed) memory

---

## Known Limitations

**Relationship directionality.** When a sentence contains multiple entities and a relationship keyword, the pairing uses positional order (`persons[0]`, `orgs[0]`) rather than syntactic dependency parsing. This occasionally inverts relationships (e.g., `Meta FOUNDER_OF Kunal Shah` instead of `Kunal Shah APPOINTED_AS Meta`) when sentence word order doesn't match the default positional assumption. A full fix requires spaCy dependency parsing or a fine-tuned relation extraction model.

**Wikidata coverage gaps.** Smaller, regional companies (Indian fintech startups, sector-specific firms) often have thin or missing Wikidata entries, causing them to resolve as `UNKNOWN` and be excluded from relationship extraction. This is a real long-tail limitation of any Wikidata-based disambiguation system, not specific to this implementation.

**Small local LLM instruction-following.** Llama 3.1 8B occasionally falls back on its own training knowledge when context is sparse, sometimes narrating that it's doing so ("although this isn't in the provided context..."). Larger frontier models (GPT-4-class, Claude 3.5+) are significantly more reliable at strict context-grounding. For production use, the Gemini verification layer partially mitigates this.

**Ollama runs outside Docker.** The `streamlit_app` container connects to Ollama via `host.docker.internal:11434` — Ollama must be running natively on the host machine. This is pragmatic for Apple Silicon (GPU passthrough into Docker containers is poorly supported on macOS ARM), but means the system isn't fully self-contained in Docker.

---

## Future Work

### Near-term (would implement next)

**Dependency-parsed relationship extraction.** Replace positional entity pairing with spaCy's dependency tree to correctly identify syntactic subject/object roles in each sentence. Eliminates the directional inversion bug entirely.

**Fine-tuned Llama on financial text.** Fine-tuning Llama 3.1 on Indian financial news, earnings reports, and regulatory filings would significantly improve entity recognition, domain-specific reasoning, and instruction-following on "use only the context" constraints. Requires GPU compute (A100-class) — not feasible on Apple Silicon, but straightforward on a cloud VM.

**Richer graph schema.** Current schema stores entities and basic relationships. Adding temporal properties (when was this relationship true?), confidence scores (how certain is this extraction?), and source provenance (which article, at what date?) would make the graph genuinely queryable for time-series analysis — relevant for tracking CEO tenure, company acquisitions, etc.

**GLiNER for zero-shot NER.** Replacing Flair's fixed-category model (`ner` tags only PER/ORG/LOC/MISC) with GLiNER's zero-shot entity recognition would allow domain-specific entity types (PRODUCT, REGULATION, FINANCIAL_METRIC) without retraining. Significantly better precision on financial text in preliminary evaluations.

### Longer-term

**Multi-hop graph reasoning.** Current graph traversal is one-hop (entities directly connected to query entities). A proper graph reasoning layer using PathRAG or similar would answer questions like "which companies are connected to Anthropic through two degrees of investment relationships" — a real GraphRAG capability this implementation approximates but doesn't fully realize.

**Evaluation framework (leakage-free).** Current system has no quantitative evaluation. A proper benchmark would use a held-out question set with ground-truth answers from the knowledge graph, measured against a naive RAG baseline, with strict temporal leakage controls (test questions only cover events after the training data cutoff). This is the gap between "it seems to work" and a publishable ICAIF paper contribution.

**Streaming responses.** Current architecture waits for the full Ollama response before displaying anything. Streaming (supported by both `ollama` and `google-genai` libraries) would make the UI feel significantly faster, especially for longer answers.

**API layer.** Exposing the query pipeline as a FastAPI REST endpoint would allow this to serve as a backend for other applications — mobile apps, Slack bots, automated research pipelines.

---

## Paper/Publication Notes

This project targets **ACM ICAIF 2026** (International Conference on AI in Finance) or the **NeurIPS 2026 Financial AI Workshop**.

**Novel contribution:** Graph-augmented hybrid RAG with Wikidata-based entity disambiguation for financial knowledge retrieval. Closest existing work (Microsoft GraphRAG, FinMem, TradingAgents) uses either static graphs or naive RAG without relationship-aware traversal. The specific contribution of dynamic entity disambiguation via Wikidata's live knowledge base (rather than a trained NER model or static ontology) is, to our knowledge, not previously described in the financial AI RAG literature.

**Related work:**
- Microsoft GraphRAG (Edge et al., 2024) — global/local graph community summarization, different problem framing
- TradingAgents (AAAI 2025) — multi-agent trading, no knowledge graph component
- FinMem (IEEE Transactions on Big Data) — memory-augmented LLM for finance, no graph retrieval
- FINSABER — leakage detection in financial AI, relevant for evaluation methodology

---

## License

MIT