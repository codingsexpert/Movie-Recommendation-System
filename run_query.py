import sys
from entity_resolver import resolve_query_entities
from query_classifier import classify_query
from graph_handler import handle_graph_query
from similarity_handler import handle_similarity_query
from config import close_connections

def process_query(query: str):
    """Universal flow for handling user query in GraphRAG engine."""
    print("\n═══════════════════════════════════════════")

    # Step 1: Entity Resolution
    print("\n🔍 ENTITY RESOLUTION")
    resolved = resolve_query_entities(query)

    # Step 2: Classification
    print("\n🧠 CLASSIFICATION")
    classification = classify_query(query, resolved)
    query_type = classification.get("type", "graph")
    reasoning = classification.get("reasoning", "")
    print(f"   Type: {query_type} | Reason: {reasoning}")

    # Step 3: Route to handler
    if query_type == "similarity":
        print("\n📐 → SIMILARITY handler (Pinecone + Neo4j)...")
        answer = handle_similarity_query(query, resolved)
    else:
        print("\n🗄️  → GRAPH handler (Neo4j)...")
        answer = handle_graph_query(query, resolved)

    print("\n═══════════════════════════════════════════")
    print("💬 Answer:\n")
    print(answer)
    print("\n═══════════════════════════════════════════")

def start_cli():
    """Interactive CLI interface."""
    print("===========================================")
    print("   🎬 GraphRAG Movie Query System (Python)")
    print("===========================================")
    print('Type your question. Type "exit" to quit.\n')

    # Single argument query mode: python run_query.py "query"
    if len(sys.argv) > 1 and sys.argv[1].strip() and sys.argv[1].lower() != "exit":
        query = " ".join(sys.argv[1:]).strip()
        try:
            process_query(query)
        except Exception as err:
            print(f"\n❌ Error: {err}")
        finally:
            close_connections()
        return

    # Interactive loop
    while True:
        try:
            user_input = input("🎬 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            close_connections()
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("\n👋 Goodbye!")
            close_connections()
            break

        try:
            process_query(user_input)
        except Exception as err:
            print(f"\n❌ Error: {err}")

if __name__ == "__main__":
    start_cli()
