import json
import re
from config import llm, driver

_INTENT_CACHE = {}

def extract_intent_and_entities_regex(query: str) -> dict | None:
    """Fast regex fallback to avoid LLM calls for very obvious queries."""
    q = query.strip().lower()
    
    # Similarity intent regexes
    sim_patterns = [
        r"(?:recommend\s+)?movies?\s+similar\s+to\s+(.+)",
        r"(?:recommend\s+)?something\s+similar\s+to\s+(.+)",
        r"similar\s+to\s+(.+)",
        r"movies?\s+like\s+(.+)",
        r"like\s+(.+)",
        r"(.+)\s+jaisi\s+movies?",
        r"(.+)\s+jaisa\s+movies?"
    ]
    
    for pattern in sim_patterns:
        match = re.search(pattern, q)
        if match:
            entity = match.group(1).strip().strip("?.\"”'")
            if entity:
                return {"type": "similarity", "entities": [entity]}
                
    # Graph intent regexes
    graph_patterns = [
        r"tell\s+me\s+about\s+(.+)",
        r"info\s+on\s+(.+)",
        r"explore\s+(.+)",
        r"directed\s+by\s+(.+)",
        r"films?\s+by\s+(.+)",
        r"movies?\s+by\s+(.+)",
        r"(.+)\s+ki\s+movies?",
        r"(.+)\s+acted\s+in"
    ]
    
    for pattern in graph_patterns:
        match = re.search(pattern, q)
        if match:
            entity = match.group(1).strip().strip("?.\"”'")
            if entity:
                return {"type": "graph", "entities": [entity]}
                
    return None

def resolve_intent_and_entities_llm(query: str) -> dict:
    """Uses a single LLM prompt to classify intent AND extract entities simultaneously."""
    q_key = query.strip().lower()
    if q_key in _INTENT_CACHE:
        return _INTENT_CACHE[q_key]

    # Quick fast-path fallback for simple queries
    regex_res = extract_intent_and_entities_regex(query)
    if regex_res:
        print(f"   ⚡ Fast regex intent resolution: {regex_res}")
        _INTENT_CACHE[q_key] = regex_res
        return regex_res

    prompt = """You are a movie knowledge graph assistant analyzing a user's query (in English, Hindi, or Hinglish).
Your task is to return a JSON object with two fields:
1. "type": The intent of the query. Must be exactly "graph" or "similarity".
   - Use "similarity" ONLY if the user wants recommendations based on similarity to a movie (e.g. "movies like Inception", "recommend similar to Matrix", "Sholay jaisi movies").
   - Use "graph" for EVERYTHING else (facts, lists, counting, filtering, actor/director searches like "movies by Nolan", "Oscar winning movies").
2. "entities": A JSON array of strings containing ONLY the specific names, titles, and terms from the query.
   - DO NOT extract generic words (movies, recommend, find, like, best, latest, jaisi, acchi).
   - DO extract: person names, movie titles, genre names, theme names, award names.

Respond ONLY with valid JSON. No markdown, no backticks.
Example Output:
{"type": "graph", "entities": ["Christopher Nolan"]}
{"type": "similarity", "entities": ["Inception"]}
{"type": "graph", "entities": ["Sci-fi", "Oscar"]}"""

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
        
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        parsed = json.loads(raw)
        _INTENT_CACHE[q_key] = parsed
        return parsed
    except Exception as e:
        print(f"⚠️ Unified LLM call failed ({e}), using fallback regex...")
        words = re.findall(r"\b[A-Z][a-zA-Z0-9]+\b", query)
        fallback_entities = [w for w in words if w.lower() not in ["recommend", "movies", "similar", "to", "the", "like"]]
        q_lower = query.lower()
        intent = "similarity" if any(k in q_lower for k in ["similar", "recommend", "like", "jaisi"]) else "graph"
        return {"type": intent, "entities": fallback_entities}

def resolve_entity(entity_name: str) -> list[dict]:
    """Resolve ONE entity across ALL node types in Neo4j using a single optimized query."""
    matches = []
    if not driver:
        return matches

    try:
        with driver.session() as session:
            exact_cypher = """
                MATCH (n)
                WHERE (n:Movie OR n:Director OR n:Actor OR n:Genre OR n:Theme OR n:Award)
                  AND toLower(COALESCE(n.title, n.name)) = toLower($name)
                RETURN COALESCE(n.title, n.name) AS nodeName, labels(n)[0] AS label
                LIMIT 5
            """
            exact_res = session.run(exact_cypher, name=entity_name)
            for rec in exact_res:
                matches.append({"searchTerm": entity_name, "label": rec["label"], "nodeName": rec["nodeName"], "matchType": "exact"})

            if matches: return matches

            partial_cypher = """
                MATCH (n)
                WHERE (n:Movie OR n:Director OR n:Actor OR n:Genre OR n:Theme OR n:Award)
                  AND toLower(COALESCE(n.title, n.name)) CONTAINS toLower($name)
                RETURN COALESCE(n.title, n.name) AS nodeName, labels(n)[0] AS label
                LIMIT 5
            """
            partial_res = session.run(partial_cypher, name=entity_name)
            for rec in partial_res:
                matches.append({"searchTerm": entity_name, "label": rec["label"], "nodeName": rec["nodeName"], "matchType": "partial"})

    except Exception as e:
        print(f"⚠️ Neo4j query error during entity resolution ({e})")

    if matches: return matches

    if driver:
        try:
            import difflib
            with driver.session() as session:
                res = session.run("MATCH (n) WHERE (n:Movie OR n:Director OR n:Actor) RETURN COALESCE(n.title, n.name) AS name LIMIT 150")
                all_names = [r["name"] for r in res if r["name"]]
                close = difflib.get_close_matches(entity_name, all_names, n=1, cutoff=0.6)
                if close:
                    matches.append({"searchTerm": entity_name, "label": "Movie/Person", "nodeName": close[0], "matchType": "fuzzy"})
        except Exception as err:
            pass

    return matches

def process_query_intent(query: str) -> tuple[dict, dict]:
    """
    Extracts intent and entities via a single LLM call, resolves entities in Neo4j,
    and returns (classification, resolved_entities).
    """
    print("   🔍 Step 1: Extracting Intent & Entities (Unified LLM Call)...")
    result = resolve_intent_and_entities_llm(query)
    
    query_type = result.get("type", "graph")
    entity_names = result.get("entities", [])
    print(f"   ✅ Intent: {query_type} | Entities: [{', '.join(entity_names)}]")

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

    classification = {"type": query_type, "reasoning": "Unified single-pass LLM"}
    resolved_dict = {"query": query, "entities": resolved, "unresolved": unresolved}
    
    return classification, resolved_dict
