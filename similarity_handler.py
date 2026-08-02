import re
from config import llm, embed_text, pinecone_index, driver

def extract_title_from_chunk(chunk_text: str) -> str | None:
    """Extract movie title from a raw chunk text."""
    match = re.search(r"Movie Title:\s*(.+)", chunk_text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def get_movie_genres(movie_title: str) -> list[str]:
    """Neo4j: Get genres of a specific movie."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (m:Movie)-[:BELONGS_TO]->(g:Genre)
            WHERE m.title = $title
            RETURN g.name AS genre
            """,
            title=movie_title
        )
        return [r["genre"] for r in result]

def get_movie_themes(movie_title: str) -> list[str]:
    """Neo4j: Get themes of a specific movie."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (m:Movie)-[:EXPLORES]->(t:Theme)
            WHERE m.title = $title
            RETURN t.name AS theme
            """,
            title=movie_title
        )
        return [r["theme"] for r in result]

def filter_by_genre(movie_titles: list[str], source_genres: list[str]) -> list[dict]:
    """Neo4j: Filter candidate movies sharing at least one genre with source movie."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (m:Movie)-[:BELONGS_TO]->(g:Genre)
            WHERE m.title IN $titles
            WITH m, collect(g.name) AS genres
            WHERE any(genre IN genres WHERE genre IN $sourceGenres)
            RETURN m.title AS title, genres
            """,
            titles=movie_titles, sourceGenres=source_genres
        )
        return [{"title": r["title"], "genres": r["genres"]} for r in result]

def fallback_vector_search(query: str) -> str:
    """Fallback: Pure vector search when no specific movie entity is resolved."""
    print("   📐 Fallback: Pure vector search...")
    query_vector = embed_text(query)

    search_results = pinecone_index.query(
        vector=query_vector,
        top_k=20,
        include_metadata=True
    )

    matches = getattr(search_results, "matches", [])
    if not matches:
        return "I couldn't find any matching movies."

    candidates = [m.metadata.get("text", "") for m in matches if m.metadata]

    formatted_candidates = "\n\n".join([
        f"--- Movie {i + 1} ---\n{text}" for i, text in enumerate(candidates)
    ])

    prompt = f"""The user asked: "{query}"

Here are {len(candidates)} movies from our database:
{formatted_candidates}

Pick the 10 BEST matches for what the user is looking for.
For each pick, explain in 1-2 sentences WHY it fits.
Do NOT mention databases, vectors, or technical terms.
Format as a numbered list."""

    response = llm.invoke([
        {"role": "system", "content": "You are a movie recommendation expert. Respond ONLY with a numbered list of movie recommendations with short explanations. Never respond with JSON."},
        {"role": "user", "content": prompt}
    ])

    answer = response.content
    if isinstance(answer, list):
        answer = " ".join([b.text if hasattr(b, "text") else str(b) for b in answer])
    return answer.strip()

def handle_similarity_query(query: str, resolved_entities: dict) -> str:
    """Main similarity handler: Pinecone + Neo4j + LLM."""
    entities = resolved_entities.get("entities", [])
    movie_entity = next((e for e in entities if e["label"] == "Movie"), None)

    if not movie_entity:
        print("   ⚠️ No movie entity resolved. Falling back to vector search...")
        return fallback_vector_search(query)

    movie_name = movie_entity["nodeName"]
    print(f"   🎬 Finding movies similar to: \"{movie_name}\"")

    # Step 2: Pinecone top 50 candidates
    print("   📐 Searching Pinecone (top 50)...")
    query_vector = embed_text(movie_name)

    search_results = pinecone_index.query(
        vector=query_vector,
        top_k=50,
        include_metadata=True
    )

    matches = getattr(search_results, "matches", [])
    if not matches:
        return "I couldn't find any similar movies."

    print(f"   ✅ Got {len(matches)} candidates from Pinecone")

    # Step 3: Get genres & themes from Neo4j
    print("   🗄️  Getting source movie genres from Neo4j...")
    source_genres = get_movie_genres(movie_name)
    source_themes = get_movie_themes(movie_name)
    print(f"   ✅ Genres: [{', '.join(source_genres)}]")
    print(f"   ✅ Themes: [{', '.join(source_themes)}]")

    if not source_genres:
        print(f"   ⚠️ No genres found for \"{movie_name}\". Using vector results only.")
        return fallback_vector_search(query)

    # Step 4: Extract titles from top 50 chunks
    candidate_titles = []
    chunk_map = {}

    for match in matches:
        metadata = match.metadata or {}
        text = metadata.get("text", "")
        title = extract_title_from_chunk(text)
        if title and title.lower() != movie_name.lower():
            candidate_titles.append(title)
            chunk_map[title] = text

    print(f"   ✅ Extracted {len(candidate_titles)} movie titles from chunks")

    # Step 5: Filter by genre match in Neo4j
    print("   🗄️  Filtering by genre in Neo4j...")
    genre_matched = filter_by_genre(candidate_titles, source_genres)
    print(f"   ✅ {len(genre_matched)} movies share at least one genre")

    if not genre_matched:
        return f"I found movies in the database but none share genres with \"{movie_name}\" ({', '.join(source_genres)}). Try a broader search."

    # Step 6: LLM top 10 selection
    print("   🤖 LLM selecting top 10...")
    candidate_list = [
        {
            "title": m["title"],
            "genres": ", ".join(m["genres"]),
            "chunkText": chunk_map.get(m["title"], "")
        }
        for m in genre_matched
    ]

    formatted_list = "\n\n".join([
        f"- {c['title']} [Genres: {c['genres']}]\n  Info: {c['chunkText']}"
        for c in candidate_list
    ])

    prompt = f"""The user wants movies similar to: "{movie_name}"
  - Genres: {', '.join(source_genres)}
  - Themes: {', '.join(source_themes)}

Here are {len(candidate_list)} movies that share at least one genre:
{formatted_list}

Pick the 10 BEST matches. Rank by:
1. Genre overlap (most important)
2. Theme similarity (from the chunk text)
3. Overall vibe/style match

For each pick, explain in 1-2 sentences WHY it's similar.
Do NOT mention databases, vectors, scores, or technical terms.
Format as a numbered list."""

    response = llm.invoke([
        {"role": "system", "content": "You are a movie recommendation expert. Respond ONLY with a numbered list of movie recommendations with short explanations. Never respond with JSON."},
        {"role": "user", "content": prompt}
    ])

    answer = response.content
    if isinstance(answer, list):
        answer = " ".join([b.text if hasattr(b, "text") else str(b) for b in answer])
    return answer.strip()
