import json
import re
from config import driver, llm
from cypher_templates import build_cypher

def create_query_plan(query: str, resolved_entities: dict) -> dict:
    """Create query plan using LLM with resolved entity context."""
    entities = resolved_entities.get("entities", [])
    unresolved = resolved_entities.get("unresolved", [])

    entity_context = "\n".join([
        f'"{e["searchTerm"]}" = {e["label"]} (exact name in DB: "{e["nodeName"]}")'
        for e in entities
    ])

    unresolved_context = (
        f"\nNOT FOUND in database: {', '.join(unresolved)}"
        if unresolved else ""
    )

    prompt = f"""You are a query planner for a movie knowledge graph.

RESOLVED ENTITIES (already verified in the database):
{entity_context}{unresolved_context}

IMPORTANT: Use the exact "nodeName" values from above in filter values.
For example, if entity resolved to Director "Christopher Nolan", use "Christopher Nolan" not "Nolan".

GRAPH SCHEMA:
Nodes: Movie(title,year), Director(name), Actor(name), Genre(name), Theme(name), Award(name,category)
Relationships: Director-[:DIRECTED]->Movie, Actor-[:ACTED_IN]->Movie, Movie-[:BELONGS_TO]->Genre, Movie-[:EXPLORES]->Theme, Movie-[:WON]->Award

OUTPUT a JSON plan using ONLY these step types:

1. "traversal": {{"type":"traversal","from":"Label","rel":"RELATIONSHIP","to":"Label"}}
2. "filter": {{"type":"filter","field":"Label.property","op":"=","value":"some value"}}
   Operators: =, <>, >, <, >=, <=, CONTAINS, STARTS WITH
3. "projection": {{"type":"projection","fields":["Label.property"],"distinct":true/false}}
4. "aggregation": {{"type":"aggregation","function":"count","field":"Label.property","alias":"name","groupBy":"Label.property"}}
5. "sort": {{"type":"sort","field":"Label.property","direction":"ASC/DESC"}}
6. "limit": {{"type":"limit","value":number}}
7. "describe": {{"type":"describe","label":"Label","name":"exact node name"}}
   → Use this when the user asks "tell me about X" or "who is X" — fetches ALL relationships around that entity
8. "path": {{"type":"path","fromLabel":"Label","fromName":"name","toLabel":"Label","toName":"name"}}
   → Use this when asking how two entities are related — finds the shortest connection

RULES:
- Award.name = award type (e.g. "Oscar"), Award.category = specific category (e.g. "Best Picture")
- Always include a projection or aggregation step (unless using describe or path)
- Use EXACT node names from the resolved entities above
- Output ONLY valid JSON. No markdown, no backticks.

EXAMPLES:

"Movies directed by Christopher Nolan" (Nolan resolved as Director "Christopher Nolan"):
{{"steps":[
  {{"type":"traversal","from":"Director","rel":"DIRECTED","to":"Movie"}},
  {{"type":"filter","field":"Director.name","op":"=","value":"Christopher Nolan"}},
  {{"type":"projection","fields":["Movie.title","Movie.year"],"distinct":true}}
]}}

"Action movies with Tom Hardy" (Action resolved as Genre, Tom Hardy as Actor):
{{"steps":[
  {{"type":"traversal","from":"Actor","rel":"ACTED_IN","to":"Movie"}},
  {{"type":"traversal","from":"Movie","rel":"BELONGS_TO","to":"Genre"}},
  {{"type":"filter","field":"Actor.name","op":"=","value":"Tom Hardy"}},
  {{"type":"filter","field":"Genre.name","op":"=","value":"Action"}},
  {{"type":"projection","fields":["Movie.title","Movie.year"],"distinct":true}}
]}}

"Tell me about Inception" (Inception resolved as Movie "Inception"):
{{"steps":[
  {{"type":"describe","label":"Movie","name":"Inception"}}
]}}

"Who is Christopher Nolan?" (Nolan resolved as Director "Christopher Nolan"):
{{"steps":[
  {{"type":"describe","label":"Director","name":"Christopher Nolan"}}
]}}

"How is Leonardo DiCaprio related to Christopher Nolan?" (DiCaprio = Actor, Nolan = Director):
{{"steps":[
  {{"type":"path","fromLabel":"Actor","fromName":"Leonardo DiCaprio","toLabel":"Director","toName":"Christopher Nolan"}}
]}}

"How many sci-fi movies?" (Sci-fi resolved as Genre "Sci-Fi"):
{{"steps":[
  {{"type":"traversal","from":"Movie","rel":"BELONGS_TO","to":"Genre"}},
  {{"type":"filter","field":"Genre.name","op":"=","value":"Sci-Fi"}},
  {{"type":"aggregation","function":"count","field":"Movie.title","alias":"total_scifi_movies"}}
]}}"""

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
        return json.loads(raw)
    except Exception:
        print("❌ Failed to parse plan:", raw[:300])
        raise RuntimeError("Query planning failed. Please rephrase your question.")

def execute_describe(label: str, name: str) -> list[dict]:
    """Fetch ALL relationships around an entity."""
    if not driver:
        return [{"error": "Neo4j database not connected"}]
    with driver.session() as session:
        params = {"name": name}

        if label == "Movie":
            cypher = """
                MATCH (m:Movie {title: $name})
                OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
                OPTIONAL MATCH (a:Actor)-[:ACTED_IN]->(m)
                OPTIONAL MATCH (m)-[:BELONGS_TO]->(g:Genre)
                OPTIONAL MATCH (m)-[:EXPLORES]->(t:Theme)
                OPTIONAL MATCH (m)-[:WON]->(aw:Award)
                RETURN m.title AS title, m.year AS year,
                       collect(DISTINCT d.name) AS directors,
                       collect(DISTINCT a.name) AS actors,
                       collect(DISTINCT g.name) AS genres,
                       collect(DISTINCT t.name) AS themes,
                       collect(DISTINCT {name: aw.name, category: aw.category}) AS awards
            """
        elif label == "Director":
            cypher = """
                MATCH (d:Director {name: $name})-[:DIRECTED]->(m:Movie)
                OPTIONAL MATCH (m)-[:BELONGS_TO]->(g:Genre)
                OPTIONAL MATCH (m)-[:EXPLORES]->(t:Theme)
                OPTIONAL MATCH (m)-[:WON]->(aw:Award)
                OPTIONAL MATCH (a:Actor)-[:ACTED_IN]->(m)
                RETURN d.name AS name,
                       collect(DISTINCT {title: m.title, year: m.year}) AS movies,
                       collect(DISTINCT g.name) AS genres,
                       collect(DISTINCT t.name) AS themes,
                       collect(DISTINCT a.name) AS collaborators,
                       collect(DISTINCT {name: aw.name, category: aw.category}) AS awards
            """
        elif label == "Actor":
            cypher = """
                MATCH (a:Actor {name: $name})-[:ACTED_IN]->(m:Movie)
                OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
                OPTIONAL MATCH (m)-[:BELONGS_TO]->(g:Genre)
                OPTIONAL MATCH (m)-[:EXPLORES]->(t:Theme)
                OPTIONAL MATCH (m)-[:WON]->(aw:Award)
                RETURN a.name AS name,
                       collect(DISTINCT {title: m.title, year: m.year}) AS movies,
                       collect(DISTINCT d.name) AS directors,
                       collect(DISTINCT g.name) AS genres,
                       collect(DISTINCT t.name) AS themes,
                       collect(DISTINCT {name: aw.name, category: aw.category}) AS awards
            """
        elif label == "Genre":
            cypher = """
                MATCH (m:Movie)-[:BELONGS_TO]->(g:Genre {name: $name})
                OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
                RETURN g.name AS name,
                       collect(DISTINCT {title: m.title, year: m.year}) AS movies,
                       collect(DISTINCT d.name) AS directors
            """
        elif label == "Theme":
            cypher = """
                MATCH (m:Movie)-[:EXPLORES]->(t:Theme {name: $name})
                OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
                RETURN t.name AS name,
                       collect(DISTINCT {title: m.title, year: m.year}) AS movies,
                       collect(DISTINCT d.name) AS directors
            """
        elif label == "Award":
            cypher = """
                MATCH (m:Movie)-[:WON]->(aw:Award {name: $name})
                OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
                RETURN aw.name AS name,
                       collect(DISTINCT {title: m.title, year: m.year, category: aw.category}) AS movies,
                       collect(DISTINCT d.name) AS directors
            """
        else:
            return [{"error": f"Unknown label: {label}"}]

        print(f"   🔒 Describe Cypher: {' '.join(cypher.split())}")
        result = session.run(cypher, params)
        records = [dict(record) for record in result]
        return records

def execute_path(from_label: str, from_name: str, to_label: str, to_name: str) -> list[dict]:
    """Find shortest path between two entities in Neo4j graph."""
    if not driver:
        return [{"error": "Neo4j database not connected"}]
    from_prop = "title" if from_label == "Movie" else "name"
    to_prop = "title" if to_label == "Movie" else "name"

    cypher = f"""
        MATCH (a:{from_label} {{{from_prop}: $fromName}}),
              (b:{to_label} {{{to_prop}: $toName}}),
              path = shortestPath((a)-[*..6]-(b))
        RETURN [node IN nodes(path) | {{
          labels: labels(node),
          name: coalesce(node.name, node.title),
          year: node.year
        }}] AS pathNodes,
        [rel IN relationships(path) | type(rel)] AS pathRels
    """

    print(f"   🔒 Path Cypher: {' '.join(cypher.split())}")

    with driver.session() as session:
        result = session.run(cypher, fromName=from_name, toName=to_name)
        records = [dict(record) for record in result]
        if not records:
            return [{"error": f"No connection found between {from_name} and {to_name}"}]
        return records

def execute_template_cypher(plan: dict) -> list[dict]:
    """Execute template-based safe Cypher query."""
    if not driver:
        return [{"error": "Neo4j database not connected"}]
    cypher, params = build_cypher(plan)
    print(f"   🔒 Cypher:\n{cypher}")
    print(f"   🔒 Params: {params}")

    with driver.session() as session:
        result = session.run(cypher, params)
        records = [dict(record) for record in result]
        return records


def handle_graph_query(query: str, resolved_entities: dict) -> str:
    """Main graph query handler with robust fallback."""
    records = []
    try:
        print("   📋 Creating query plan...")
        plan = create_query_plan(query, resolved_entities)
        print("   📋 Plan:", json.dumps(plan, indent=2))

        steps = plan.get("steps", [])
        if steps:
            first_step = steps[0]
            step_type = first_step.get("type")

            if step_type == "describe":
                print(f"   🗄️  Describing {first_step['label']}: \"{first_step['name']}\"...")
                records = execute_describe(first_step["label"], first_step["name"])
            elif step_type == "path":
                print(f"   🗄️  Finding path: {first_step['fromName']} → {first_step['toName']}...")
                records = execute_path(
                    first_step["fromLabel"], first_step["fromName"],
                    first_step["toLabel"], first_step["toName"]
                )
            else:
                print("   🗄️  Querying Neo4j...")
                records = execute_template_cypher(plan)
    except Exception as err:
        print(f"⚠️ Graph plan execution error: {err}")

    # Fallback to similarity handler if graph records are empty or errored
    if not records or (isinstance(records, list) and len(records) > 0 and isinstance(records[0], dict) and records[0].get("error")):
        print("   📐 Graph plan produced no records. Falling back to vector similarity handler...")
        from similarity_handler import handle_similarity_query
        return handle_similarity_query(query, resolved_entities)

    print(f"   🗄️  Got {len(records)} results")

    response_prompt = f"""Given the question and database results, provide a clear, natural language answer.
Do NOT mention databases, Cypher, JSON, or technical details.
Do NOT return any JSON. Only return plain English text.
Be informative and thorough — include all relevant details from the results.

Question: {query}

Database Results:
{json.dumps(records[:50], indent=2)}
{f'\n... and {len(records) - 50} more results' if len(records) > 50 else ''}"""

    try:
        response = llm.invoke([
            {"role": "system", "content": "You are a helpful movie assistant. Respond ONLY in plain English text. Never respond with JSON or code."},
            {"role": "user", "content": response_prompt}
        ])

        answer = response.content
        if isinstance(answer, list):
            answer = " ".join([b.text if hasattr(b, "text") else str(b) for b in answer])
        return answer.strip()
    except Exception as e:
        print(f"⚠️ LLM response error: {e}")
        from similarity_handler import fallback_vector_search
        return fallback_vector_search(query)
