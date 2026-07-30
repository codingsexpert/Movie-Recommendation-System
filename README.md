# 🎬 Movie Recommendation System (GraphRAG)

A powerful **GraphRAG (Graph Retrieval-Augmented Generation)** movie recommendation engine built with **Node.js**, **LangChain**, **Neo4j Graph Database**, **Pinecone Vector DB**, and **Google Gemini AI**.

---

## 🌟 Key Features

- 🧠 **Hybrid Search (Graph + Vector)**: Combines knowledge graph relationships (Neo4j) with semantic vector similarity search (Pinecone).
- 📄 **PDF Entity Extraction**: Parses movie data from raw files and builds structured entity relationships using Gemini.
- 💬 **Intelligent Querying**: Classifies query intent and executes dynamic Cypher templates or vector searches.
- ⚡ **High Performance**: Powered by modern ES modules and Google Gemini text embeddings.

---

## 🛠️ Tech Stack

- **LLM & Embeddings**: Google Gemini API (`@google/genai`, `@langchain/google-genai`)
- **Knowledge Graph**: Neo4j (`neo4j-driver`)
- **Vector Database**: Pinecone (`@pinecone-database/pinecone`)
- **Framework**: LangChain.js (`@langchain/core`)
- **PDF Parser**: `pdf-parse`

---

## 🚀 Getting Started

### 1. Prerequisites

- **Node.js** (v18 or higher)
- **Neo4j Database** (AuraDB Free or Local instance)
- **Pinecone Account** (Free tier index with `dimensions=3072` & `metric=cosine`)
- **Google Gemini API Key**

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/codingsexpert/Movie-Recommendation-System.git
cd Movie-Recommendation-System
npm install
```

### 3. Environment Setup

Copy `.env.example` to `.env` and fill in your API credentials:

```bash
cp .env.example .env
```

Edit `.env`:

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

### Test Database Connections

```bash
npm run test
```

### Run Indexing Pipeline

Index movie data and populate Neo4j + Pinecone:

```bash
npm run index
```

### Query Recommendation System

Run sample queries:

```bash
npm run query
```

---

## 📁 Project Structure

```text
├── 1_testConnection.js     # Tests Neo4j, Pinecone, and Gemini API connections
├── 2_config.js             # Centralized configuration & environment loader
├── 3_pdfParser.js          # Extracts text from PDF files
├── 4_entityExtractor.js    # Extracts entities & relationships using Gemini LLM
├── 5_graphBuilder.js       # Builds graph nodes & edges in Neo4j
├── 6_vectorStore.js        # Stores & searches vectors in Pinecone
├── 7_runIndexing.js        # Main indexing script
├── 8_cypherTemplates.js    # Predefined Cypher query templates
├── 9_entityResolver.js     # Resolves entity names & canonical references
├── 10_queryClassifier.js   # Classifies user prompts & determines retrieval strategy
├── 11_graphHandler.js      # Handles graph-based queries
├── 12_similarityHandler.js # Handles vector similarity queries
├── 13_runQuery.js          # Main CLI query runner
├── data/                   # Data directory (PDF source files)
└── .env.example            # Environment variables template
```

---

## 📄 License

[MIT](LICENSE)
