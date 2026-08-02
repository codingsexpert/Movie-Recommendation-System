from config import driver, pinecone_index, llm, embed_text, close_connections, NEO4J_URI, PINECONE_API_KEY, GEMINI_API_KEY

def test_connections():
    print("🔍 Testing all connections...\n")

    # Test 1: Neo4j
    if not NEO4J_URI or not driver:
        print("❌ Neo4j: Missing NEO4J_URI or credentials in .env file.")
    else:
        try:
            with driver.session() as session:
                result = session.run("RETURN 'Neo4j Connected!' AS message")
                record = result.single()
                print("✅ Neo4j:", record["message"])
        except Exception as err:
            print("❌ Neo4j:", str(err))

    # Test 2: Pinecone
    if not PINECONE_API_KEY or not pinecone_index:
        print("❌ Pinecone: Missing PINECONE_API_KEY in .env file.")
    else:
        try:
            stats = pinecone_index.describe_index_stats()
            total_count = getattr(stats, "total_vector_count", getattr(stats, "total_record_count", 0))
            print("✅ Pinecone: Connected | Vectors:", total_count)
        except Exception as err:
            print("❌ Pinecone:", str(err))

    # Test 3: Gemini LLM
    if not GEMINI_API_KEY or not llm:
        print("❌ Gemini LLM: Missing GEMINI_API_KEY in .env file.")
    else:
        try:
            response = llm.invoke("Say 'Gemini Connected!' and nothing else.")
            content = response.content
            if isinstance(content, list):
                content = " ".join([b.text if hasattr(b, "text") else str(b) for b in content])
            print("✅ Gemini LLM:", content.strip())
        except Exception as err:
            print("❌ Gemini LLM:", str(err))

    # Test 4: Gemini Embeddings (gemini-embedding-001 -> 3072 dimensions)
    if not GEMINI_API_KEY:
        print("❌ Gemini Embeddings: Missing GEMINI_API_KEY in .env file.")
    else:
        try:
            vector = embed_text("test")
            print(f"✅ Gemini Embeddings (gemini-embedding-001): Dimension = {len(vector)}")
            if len(vector) != 3072:
                print(f"   ⚠️ Expected 3072 dimensions, got {len(vector)}")
        except Exception as err:
            print("❌ Gemini Embeddings:", str(err))

    close_connections()

if __name__ == "__main__":
    test_connections()
