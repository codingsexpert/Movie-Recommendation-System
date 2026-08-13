import json
import re
from config import llm

_CLASSIFY_CACHE = {}

def classify_query(query: str, resolved_entities: dict) -> dict:
    """Classify query intent as 'graph' or 'similarity' using resolved entity context (with caching)."""
    q_key = query.strip().lower()
    if q_key in _CLASSIFY_CACHE:
        return _CLASSIFY_CACHE[q_key]

    entities = resolved_entities.get("entities", [])
    unresolved = resolved_entities.get("unresolved", [])

    # Fast keyword check first
    q_lower = query.lower()
    if any(k in q_lower for k in ["similar", "recommend", "like", "jaisi", "jaisa", "suggest"]):
        res = {"type": "similarity", "reasoning": "Keyword recommendation detection."}
        _CLASSIFY_CACHE[q_key] = res
        return res

    entity_context = (
        "\n".join([f'"{e["searchTerm"]}" is a {e["label"]} (full name: "{e["nodeName"]}")' for e in entities])
        if entities else "No entities were found in the database."
    )

    unresolved_context = (
        f"\nThese terms were NOT found in the database: {', '.join(unresolved)}"
        if unresolved else ""
    )

    prompt = f"""You are a query classifier for a movie knowledge graph.

RESOLVED ENTITIES (we already looked these up in the database):
{entity_context}{unresolved_context}

CLASSIFY the query as ONE of:

1. "graph" — anything that can be answered from structured data:
   - Finding movies/actors/directors based on specific criteria
   - Getting information about a specific entity
   - Finding how two entities are related
   - Counting, listing, filtering
   - Examples: "Movies directed by [Director]", "Tell me about [Movie]",
     "How is [Actor] related to [Director]?", "Action movies with [Actor]"

2. "similarity" — finding similar or recommended items based on taste:
   - The query explicitly asks for "similar", "like", "recommend"
   - The user wants to discover new things based on something they liked
   - Examples: "Movies like [Movie]", "Recommend something similar to [Movie]",
     "I liked [Movie], what else should I watch?"

Respond ONLY with JSON: {{"type": "graph" or "similarity", "reasoning": "one sentence"}}
No markdown, no backticks."""

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

        # Extract JSON object using regex
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "type" in parsed:
            _CLASSIFY_CACHE[q_key] = parsed
            return parsed
    except Exception as err:
        print(f"⚠️ Query classification LLM call failed ({err}), falling back to keyword classification...")

    # Keyword fallback edge case handling
    if any(k in q_lower for k in ["similar", "recommend", "like", "jaisi", "jaisa"]):
        res = {"type": "similarity", "reasoning": "Keyword fallback detection for recommendations."}
        _CLASSIFY_CACHE[q_key] = res
        return res

    print("⚠️ Classification failed, defaulting to graph")
    res = {"type": "graph", "reasoning": "Default classification fallback."}
    _CLASSIFY_CACHE[q_key] = res
    return res

