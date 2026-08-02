import sys
import time
from entity_extractor import extract_all_entities
from graph_builder import build_graph
from vector_store import build_vector_store
from config import close_connections

def run_indexing(pdf_path: str = './data/movies.pdf'):
    print("===========================================")
    print("   🎬 GraphRAG Indexing Pipeline (Python)")
    print("===========================================\n")

    start_time = time.time()

    try:
        # ── STEP 1: Extract Entities from PDF (Gemini) ──
        print("── STEP 1: Extracting Entities (Gemini + PDF Upload) ──")
        entities = extract_all_entities(pdf_path)

        # ── STEP 2: Build Neo4j Graph ──
        print("\n── STEP 2: Building Graph (Neo4j) ──")
        build_graph(entities)

        # ── STEP 3: Build Vector Store (Parse PDF -> Chunk -> Embed -> Pinecone) ──
        print("\n── STEP 3: Building Vector Store (Pinecone) ──")
        build_vector_store(pdf_path)

        elapsed = round(time.time() - start_time, 1)
        print("\n===========================================")
        print(f"   ✅ Indexing complete in {elapsed}s")
        print("===========================================")
    except Exception as err:
        print(f"\n❌ Indexing failed: {err}")
        import traceback
        traceback.print_exc()
    finally:
        close_connections()

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else './data/movies.pdf'
    run_indexing(pdf_path)
