# 🎬 MovieGraph AI — Intelligent Cinema Discovery Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Neo4j-Graph_DB-4581C3?style=for-the-badge&logo=neo4j&logoColor=white" />
  <img src="https://img.shields.io/badge/Pinecone-Vector_DB-000000?style=for-the-badge&logo=pinecone&logoColor=white" />
  <img src="https://img.shields.io/badge/Gemini_AI-LLM-4285F4?style=for-the-badge&logo=google&logoColor=white" />
</p>

A production-grade **GraphRAG (Graph Retrieval-Augmented Generation)** movie recommendation engine that combines **Knowledge Graphs**, **Vector Similarity Search**, and **Large Language Models** to deliver Netflix-quality cinematic discovery.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 **Hybrid GraphRAG Search** | Combines Neo4j graph traversal with Pinecone vector similarity for accurate recommendations |
| 🎬 **Netflix-Style UI** | Poster-dominant cards, hero spotlight rotation, trailer modal, dark/light theme |
| 💬 **Natural Language Queries** | Ask in English or Hinglish — *"Nolan ki best movie konsi hai?"* |
| 🔍 **Fuzzy Entity Matching** | Typo-tolerant search — *"Interstelar"* → *Interstellar* |
| 📊 **Knowledge Graph Visualizer** | Interactive 2D graph powered by Vis.js |
| 🎥 **YouTube Trailer Player** | Watch trailers in an embedded modal popup |
| 📄 **PDF Ingestion Pipeline** | Upload movie PDFs → auto-extract entities → build graph + vectors |
| ⚡ **Smart Caching** | Redis / in-memory TTL cache to avoid redundant LLM calls |
| 📈 **User Interaction Tracking** | Logs user behavior for personalized recommendations |
| 🔄 **TMDB Sync** | Fetch trending movies from TMDB API automatically |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vanilla JS)                     │
│  Netflix-Style UI · Poster Cards · Graph Viz · Trailer Modal│
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend (Python)                   │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │   Intent     │  │   Entity     │  │   Query           │  │
│  │   Resolver   │  │   Resolver   │  │   Classifier      │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬──────────┘  │
│         └────────────────┼───────────────────┘              │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              GraphRAG Pipeline Router                 │   │
│  │   graph_handler.py  ←→  similarity_handler.py        │   │
│  └──────────┬───────────────────────┬───────────────────┘   │
│             │                       │                       │
└─────────────┼───────────────────────┼───────────────────────┘
              ▼                       ▼
   ┌──────────────────┐    ┌──────────────────┐
   │   Neo4j Graph DB │    │  Pinecone Vector  │
   │   (Knowledge     │    │  DB (Semantic     │
   │    Graph)        │    │   Embeddings)     │
   └──────────────────┘    └──────────────────┘
              │                       │
              └───────────┬───────────┘
                          ▼
               ┌─────────────────┐
               │  Google Gemini  │
               │  (LLM + Embed) │
               └─────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **LLM** | Google Gemini 2.5 Flash |
| **Embeddings** | Gemini Embedding 001 (3072-dim) |
| **Knowledge Graph** | Neo4j (AuraDB / Local) |
| **Vector Database** | Pinecone (Cosine Similarity) |
| **Caching** | Redis / In-Memory TTLCache |
| **Frontend** | Vanilla HTML, CSS, JavaScript |
| **Visualization** | Vis.js (Graph), Marked.js (Markdown) |
| **PDF Parsing** | PyPDF |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Neo4j Database** (AuraDB Free or local instance)
- **Pinecone Account** (Free tier, index with `dimensions=3072`, `metric=cosine`)
- **Google Gemini API Key**

### Installation

```bash
# Clone the repository
git clone https://github.com/codingsexpert/Movie-Recommendation-System.git
cd Movie-Recommendation-System

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
GEMINI_API_KEY=your_gemini_api_key
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=movie-embeddings
```

### Run the Server

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8050 --reload
```

Open **http://localhost:8050** in your browser.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stats` | Database connection status & node counts |
| `GET` | `/api/health` | Server health check |
| `GET` | `/api/catalog` | Full movie catalog with TMDB posters |
| `GET` | `/api/all_movies` | List of all movie titles |
| `GET` | `/api/movie/{title}` | Single movie details |
| `POST` | `/api/query` | GraphRAG natural language search |
| `GET` | `/api/graph_subnetwork/{entity}` | Knowledge graph subnetwork |
| `GET` | `/api/compare?movie1=X&movie2=Y` | Side-by-side movie comparison |
| `POST` | `/api/upload_pdf` | Upload & index new movie PDF |
| `POST` | `/api/track` | Log user interaction events |

---

## 📁 Project Structure

```
├── app.py                  # FastAPI main application & API routes
├── config.py               # Environment config, DB connections, embeddings
├── intent_resolver.py      # Unified intent + entity resolution (single LLM call)
├── graph_handler.py        # Neo4j Cypher query execution
├── similarity_handler.py   # Pinecone vector similarity search
├── cypher_templates.py     # Dynamic Cypher query templates
├── cache_manager.py        # Redis / TTLCache response caching
├── tracking_handler.py     # User interaction tracking API
├── sync_tmdb.py            # TMDB trending movies sync
├── entity_extractor.py     # PDF entity extraction with Gemini
├── graph_builder.py        # Neo4j graph construction
├── vector_store.py         # Pinecone vector upsert/query
├── pdf_parser.py           # PDF text extraction
├── run_indexing.py         # Full indexing pipeline
├── run_query.py            # CLI query runner
├── test_connection.py      # Connection health tests
├── static/
│   ├── index.html          # Netflix-style frontend
│   ├── style.css           # Premium bluish-white design system
│   └── app.js              # Frontend logic & poster card renderer
├── data/                   # PDF source files & uploads
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
└── .gitignore
```

---

## 🧪 Test Connections

```bash
python test_connection.py
```

---

## 📄 License

[MIT](LICENSE)

---

<p align="center">
  Built with ❤️ using GraphRAG · Neo4j · Pinecone · Google Gemini
</p>
