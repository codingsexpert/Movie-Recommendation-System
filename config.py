import os
from dotenv import load_dotenv
from neo4j import GraphDatabase, AsyncGraphDatabase
from pinecone import Pinecone
from langchain_google_genai import ChatGoogleGenerativeAI
from google import genai

# Load .env file -> puts values into os.environ
load_dotenv()

# =====================================================================
# 1. NEO4J
# =====================================================================
NEO4J_URI = os.getenv("NEO4J_URI", "").strip()
if "+s://" in NEO4J_URI:
    NEO4J_URI = NEO4J_URI.replace("+s://", "+ssc://")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j").strip()
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "").strip()

driver = None
async_driver = None
if NEO4J_URI:
    try:
        temp_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
            connection_timeout=2.0
        )
        temp_driver.verify_connectivity()
        driver = temp_driver
        
        async_driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
            connection_timeout=2.0
        )
        print("✅ Neo4j: Connected and verified connectivity (Sync & Async)!")
    except Exception as e:
        print(f"⚠️ Warning initializing Neo4j driver (using fallback vector/similarity mode): {e}")
        driver = None
        async_driver = None


# =====================================================================
# 2. PINECONE
# =====================================================================
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "").strip()
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "movie-embeddings").strip()

pc = None
pinecone_index = None
if PINECONE_API_KEY:
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        pinecone_index = pc.Index(PINECONE_INDEX_NAME)
    except Exception as e:
        print(f"⚠️ Warning initializing Pinecone: {e}")

# =====================================================================
# 3. GEMINI LLM & EMBEDDINGS
# =====================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

llm = None
genai_client = None

if GEMINI_API_KEY:
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key=GEMINI_API_KEY,
            temperature=0,
            max_retries=3
        )
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ Warning initializing Gemini API: {e}")

# =====================================================================
# 4. GEMINI EMBEDDINGS (gemini-embedding-001 -> 3072 dimensions)
# =====================================================================
def embed_text(text: str) -> list[float]:
    """Embed ONE text -> returns 3072-dim vector."""
    if not genai_client:
        raise ValueError("GEMINI_API_KEY is not configured in .env")
    
    response = genai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    if hasattr(response, "embedding") and response.embedding and response.embedding.values:
        return response.embedding.values
    elif hasattr(response, "embeddings") and response.embeddings and len(response.embeddings) > 0:
        return response.embeddings[0].values
    else:
        raise ValueError("Unexpected embedding response structure")

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed MULTIPLE texts -> returns list of 3072-dim vectors."""
    if not genai_client:
        raise ValueError("GEMINI_API_KEY is not configured in .env")

    response = genai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=texts
    )
    if hasattr(response, "embeddings") and response.embeddings:
        return [e.values for e in response.embeddings]
    elif hasattr(response, "embedding") and response.embedding:
        return [response.embedding.values]
    else:
        raise ValueError("Unexpected embeddings response structure")

def close_connections():
    """Close Neo4j driver connection."""
    global driver
    if driver:
        driver.close()
        print("✅ All connections closed.")
