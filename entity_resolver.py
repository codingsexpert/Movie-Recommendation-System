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
    prompt = """You extract entity names from movie-related queries in English, Hindi, or Hinglish.

Extract ALL names, titles, and specific terms from the query.
Do NOT extract generic English or Hindi words like "movies", "recommend", "find", "show", "batao", "dikhao", "konsi", "sabse", "acchi", "mast", "jaisi", "wale".
Do NOT extract generic adjectives like "good", "best", "latest".
DO extract: person names, movie titles, genre names, theme names, award names.

Respond ONLY with a JSON array of strings. No markdown, no backticks.

Examples:
"Movies directed by Christopher Nolan" → ["Christopher Nolan"]
"Nolan ki sabse acchi movie konsi hai" → ["Nolan"]
"Inception jaisi 5 mast movies batao" → ["Inception"]
"Action movies with Tom Hardy" → ["Action", "Tom Hardy"]
"DiCaprio ki oscar wale films" → ["DiCaprio", "oscar"]
"Tell me about Inception" → ["Inception"]
"Movies like Inception" → ["Inception"]
"Sci-fi movies that won Oscar" → ["Sci-fi", "Oscar"]"""

# Simple in-memory cache for entity extraction
_ENTITY_CACHE = {}

def extract_entities_regex(query: str) -> list[str] | None:
    q = query.strip().strip("?").strip(".").strip()
    
    # Patterns to match and extract
    patterns = [
        r"(?:recommend\s+)?movies?\s+similar\s+to\s+(.+)",
        r"(?:recommend\s+)?something\s+similar\s+to\s+(.+)",
        r"similar\s+to\s+(.+)",
        r"movies?\s+like\s+(.+)",
        r"like\s+(.+)",
        r"tell\s+me\s+about\s+(.+)",
        r"info\s+on\s+(.+)",
        r"explore\s+(.+)",
        r"directed\s+by\s+(.+)",
        r"films?\s+by\s+(.+)",
        r"movies?\s+by\s+(.+)",
        r"(.+)\s+jaisi\s+movies?",
        r"(.+)\s+jaisa\s+movies?",
        r"(.+)\s+ki\s+movies?",
        r"(.+)\s+acted\s+in",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, q, re.IGNORECASE)
        if match:
            entity = match.group(1).strip()
            entity = re.sub(r"^['\"“]+|['\"”]+$", "", entity).strip()
            if entity and len(entity) < 50:
                return [entity]
    return None

def extract_entities(query: str) -> list[str]:
    """Extract entity names from user query using regex first, then caching + Gemini LLM."""
    q_key = query.strip().lower()
    if q_key in _ENTITY_CACHE:
        return _ENTITY_CACHE[q_key]

    regex_res = extract_entities_regex(query)
    if regex_res is not None:
        print(f"   ⚡ Fast regex entity extraction: {regex_res}")
        _ENTITY_CACHE[q_key] = regex_res
        return regex_res

    prompt = """You extract entity names from movie-related queries in English, Hindi, or Hinglish.

Extract ALL names, titles, and specific terms from the query.
Do NOT extract generic English or Hindi words like "movies", "recommend", "find", "show", "batao", "dikhao", "konsi", "sabse", "acchi", "mast", "jaisi", "wale".
Do NOT extract generic adjectives like "good", "best", "latest".
DO extract: person names, movie titles, genre names, theme names, award names.

Respond ONLY with a JSON array of strings. No markdown, no backticks.

Examples:
"Movies directed by Christopher Nolan" → ["Christopher Nolan"]
"Nolan ki sabse acchi movie konsi hai" → ["Nolan"]
"Inception jaisi 5 mast movies batao" → ["Inception"]
"Action movies with Tom Hardy" → ["Action", "Tom Hardy"]
"DiCaprio ki oscar wale films" → ["DiCaprio", "oscar"]
"Tell me about Inception" → ["Inception"]
"Movies like Inception" → ["Inception"]
"Sci-fi movies that won Oscar" → ["Sci-fi", "Oscar"]"""

    try:
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

        parsed = json.loads(raw)
        result = parsed if isinstance(parsed, list) else []
        _ENTITY_CACHE[q_key] = result
        return result
    except Exception as e:
        print(f"⚠️ Entity extraction LLM call failed ({e}), using fallback regex...")
        words = re.findall(r"\b[A-Z][a-zA-Z0-9]+\b", query)
        fallback_res = [w for w in words if w.lower() not in ["recommend", "movies", "similar", "to", "the"]]
        return fallback_res

def resolve_entity(entity_name: str) -> list[dict]:
    """Resolve ONE entity across ALL node types in Neo4j (Exact match first, then CONTAINS) using a single optimized query."""
    matches = []
    if not driver:
        return matches

    try:
        with driver.session() as session:
            # 1. Exact match across all relevant labels in ONE query
            exact_cypher = """
                MATCH (n)
                WHERE (n:Movie OR n:Director OR n:Actor OR n:Genre OR n:Theme OR n:Award)
                  AND toLower(COALESCE(n.title, n.name)) = toLower($name)
                RETURN COALESCE(n.title, n.name) AS nodeName, labels(n)[0] AS label
                LIMIT 5
            """
            exact_res = session.run(exact_cypher, name=entity_name)
            for rec in exact_res:
                matches.append({
                    "searchTerm": entity_name,
                    "label": rec["label"],
                    "nodeName": rec["nodeName"],
                    "matchType": "exact"
                })

            if matches:
                return matches

            # 2. Partial match across all relevant labels in ONE query
            partial_cypher = """
                MATCH (n)
                WHERE (n:Movie OR n:Director OR n:Actor OR n:Genre OR n:Theme OR n:Award)
                  AND toLower(COALESCE(n.title, n.name)) CONTAINS toLower($name)
                RETURN COALESCE(n.title, n.name) AS nodeName, labels(n)[0] AS label
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

    except Exception as e:
        print(f"⚠️ Neo4j query error during entity resolution ({e})")

    if matches:
        return matches

    # 3. Fuzzy match fallback
    if driver:
        try:
            import difflib
            with driver.session() as session:
                # Optimized fuzzy match lookup - only pull 150 total records
                res = session.run("""
                    MATCH (n)
                    WHERE (n:Movie OR n:Director OR n:Actor)
                    RETURN COALESCE(n.title, n.name) AS name LIMIT 150
                """)
                all_names = [r["name"] for r in res if r["name"]]
                close = difflib.get_close_matches(entity_name, all_names, n=1, cutoff=0.6)
                if close:
                    # Very basic fallback, label is guessed
                    matches.append({
                        "searchTerm": entity_name,
                        "label": "Movie/Person",
                        "nodeName": close[0],
                        "matchType": "fuzzy"
                    })
        except Exception as err:
            pass

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

