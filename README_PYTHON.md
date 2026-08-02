# 🎬 Movie Recommendation System (GraphRAG) — Python Version

A complete **Python** implementation of the **GraphRAG (Graph Retrieval-Augmented Generation)** movie recommendation engine built with **Neo4j Graph Database**, **Pinecone Vector DB**, and **Google Gemini AI**.

---

## 🌟 Key Features

- 🧠 **Hybrid Search (Graph + Vector)**: Combines knowledge graph relationships (Neo4j) with semantic vector similarity search (Pinecone).
- 📄 **PDF Entity Extraction**: Uploads PDF directly to Gemini Files API and extracts structured entities in parallel.
- 💬 **Intelligent Querying**: Classifies query intent and executes dynamic safe Cypher templates or vector searches.
- ⚡ **High Performance**: Python 3.10+ async/parallel execution with 3072-dimensional Gemini embeddings.

---

## 🛠️ Tech Stack

- **LLM & Embeddings**: Google Gemini API (`google-genai`, `langchain-google-genai`)
- **Knowledge Graph**: Neo4j (`neo4j`)
- **Vector Database**: Pinecone (`pinecone-client`)
- **PDF Parser**: `pypdf`
- **Environment**: `python-dotenv`

---

## 🚀 Getting Started

### 1. Environment Setup

Create virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Ensure your `.env` file contains your credentials:

```env
GEMINI_API_KEY=your_gemini_api_key
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=movie-embeddings
```

---

## 💻 Usage

### 1. Test Database Connections

```bash
.venv/bin/python test_connection.py
```

### 2. Run Indexing Pipeline

Index movie data and populate Neo4j + Pinecone:

```bash
.venv/bin/python run_indexing.py ./data/movies.pdf
```

### 3. Query Recommendation System

Run interactive CLI:

```bash
.venv/bin/python run_query.py
```

Or pass a single question directly:

```bash
.venv/bin/python run_query.py "Tell me about Inception"
```

---

## 📁 File Structure

```text
├── config.py             # Database & LLM connection configuration
├── test_connection.py    # Tests Neo4j, Pinecone, Gemini LLM & Embeddings
├── pdf_parser.py         # PDF text parsing & chunking utility
├── entity_extractor.py   # Extracts entities via Gemini Files API (Parallel)
├── graph_builder.py      # Neo4j graph nodes, edges & index builder
├── vector_store.py       # Embeddings generator & Pinecone vector store builder
├── run_indexing.py       # Main indexing script (3-step pipeline)
├── cypher_templates.py   # Safe Whitelisted Cypher builder
├── entity_resolver.py    # Multi-node entity resolution in Neo4j
├── query_classifier.py  # Intent classifier (graph vs similarity)
├── graph_handler.py     # Graph RAG query handler
├── similarity_handler.py# Vector similarity & hybrid recommendation handler
├── run_query.py          # Interactive Python CLI query runner
└── requirements.txt      # Python dependencies
```
