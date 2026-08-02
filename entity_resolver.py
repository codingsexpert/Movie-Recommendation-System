import json
import re
from config import llm, driver

NODE_TYPES = [
    {"label": "Movie", "property": "title"},
    {"label": "Director", "property": "name"},
    {"label": "Actor", "property": "name"},
    {"label": "Genre", "property": "name"},
    {"label": "Theme", "property": "name"},
    {"label": "Award", "property": "name"},
]

def extract_entities(query: str) -> list[str]:
    """Extract entity names from user query using Gemini LLM."""
    prompt = """You extract entity names from movie-related queries.

Extract ALL names, titles, and specific terms from the query.
Do NOT extract generic words like "movies", "recommend", "find", "show".
Do NOT extract adjectives like "good", "best", "latest".
DO extract: person names, movie titles, genre names, theme names, award names.

Respond ONLY with a JSON array of strings. No markdown, no backticks.

Examples:
"Movies directed by Christopher Nolan" → ["Christopher Nolan"]
"Action movies with Tom Hardy" → ["Action", "Tom Hardy"]
"How is DiCaprio related to Nolan?" → ["DiCaprio", "Nolan"]
"Tell me about Inception" → ["Inception"]
"Movies like Inception" → ["Inception"]
"Sci-fi movies that won Oscar" → ["Sci-fi", "Oscar"]
"Recommend me a good thriller" → ["thriller"]
"Movies about dreams and reality" → ["dreams", "reality"]"""

    response = llm.invoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": query}
    ])

    raw = response.content
    if isinstance(raw, list):
        raw = " ".join([b.text if hasattr(b, "text") else str(b) for b in raw])
    raw = raw.strip()
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw).strip()

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        print("⚠️ Entity extraction failed, returning empty array")
        return []

def resolve_entity(entity_name: str) -> list[dict]:
    """Resolve ONE entity across ALL node types in Neo4j (Exact match first, then CONTAINS)."""
    matches = []

    with driver.session() as session:
        for node_type in NODE_TYPES:
            label = node_type["label"]
            property_name = node_type["property"]

            # 1. Exact match (case-insensitive)
            exact_cypher = f"""
                MATCH (n:{label})
                WHERE toLower(n.{property_name}) = toLower($name)
                RETURN n.{property_name} AS nodeName, labels(n)[0] AS label
                LIMIT 5
            """
            exact_res = session.run(exact_cypher, name=entity_name)
            exact_records = list(exact_res)

            if exact_records:
                for rec in exact_records:
                    matches.append({
                        "searchTerm": entity_name,
                        "label": rec["label"],
                        "nodeName": rec["nodeName"],
                        "matchType": "exact"
                    })
                continue

            # 2. Partial match (CONTAINS)
            partial_cypher = f"""
                MATCH (n:{label})
                WHERE toLower(n.{property_name}) CONTAINS toLower($name)
                RETURN n.{property_name} AS nodeName, labels(n)[0] AS label
                LIMIT 5
            """
            partial_res = session.run(partial_cypher, name=entity_name)
            for rec in partial_res:
                matches.append({
                    "searchTerm": entity_name,
                    "label": rec["label"],
                    "nodeName": rec["nodeName"],
                    "matchType": "partial"
                })

    exact_matches = [m for m in matches if m["matchType"] == "exact"]
    if exact_matches:
        return exact_matches

    return matches

def resolve_query_entities(query: str) -> dict:
    """Extract entities from query -> Resolve each in Neo4j."""
    print("   🔍 Step 1: Extracting entities from query...")
    entity_names = extract_entities(query)
    print(f"   ✅ Found: [{', '.join(entity_names)}]")

    if not entity_names:
        return {"query": query, "entities": [], "unresolved": []}

    print("   🗄️  Step 2: Resolving entities in Neo4j...")
    resolved = []
    unresolved = []

    for name in entity_names:
        matches = resolve_entity(name)
        if matches:
            for match in matches:
                resolved.append(match)
                print(f"   ✅ \"{name}\" → {match['label']} ({match['nodeName']}) [{match['matchType']}]")
        else:
            unresolved.append(name)
            print(f"   ❌ \"{name}\" → not found in graph")

    return {"query": query, "entities": resolved, "unresolved": unresolved}
