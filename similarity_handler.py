import re
from config import llm, embed_text, pinecone_index, async_driver

def extract_title_from_chunk(chunk_text: str) -> str | None:
    """Extract movie title from a raw chunk text with multiple fallback regex patterns."""
    if not chunk_text:
        return None
    match = re.search(r"(?:Movie Title|Title|Movie):\s*(.+)", chunk_text, re.IGNORECASE)
    if match:
        return match.group(1).split("\n")[0].strip()
    first_line = chunk_text.strip().split("\n")[0]
    first_line_clean = re.sub(r"^[#\*\d\.\s\-\:]+", "", first_line).strip()
    if 2 <= len(first_line_clean) <= 60:
        return first_line_clean
    return None

async def get_movie_genres(movie_title: str) -> list[str]:
    """Neo4j: Get genres of a specific movie."""
    if not async_driver:
        return []
    try:
        async with async_driver.session() as session:
            result = await session.run(
                """
                MATCH (m:Movie)-[:BELONGS_TO]->(g:Genre)
                WHERE toLower(m.title) = toLower($title)
                RETURN g.name AS genre
                """,
                title=movie_title
            )
            return [r["genre"] async for r in result]
    except Exception as e:
        print(f"⚠️ Neo4j error in get_movie_genres: {e}")
        return []

async def get_movie_themes(movie_title: str) -> list[str]:
    """Neo4j: Get themes of a specific movie."""
    if not async_driver:
        return []
    try:
        async with async_driver.session() as session:
            result = await session.run(
                """
                MATCH (m:Movie)-[:EXPLORES]->(t:Theme)
                WHERE toLower(m.title) = toLower($title)
                RETURN t.name AS theme
                """,
                title=movie_title
            )
            return [r["theme"] async for r in result]
    except Exception as e:
        print(f"⚠️ Neo4j error in get_movie_themes: {e}")
        return []

async def filter_by_genre(movie_titles: list[str], source_genres: list[str]) -> list[dict]:
    """Neo4j: Filter candidate movies sharing at least one genre with source movie."""
    if not async_driver or not movie_titles or not source_genres:
        return []
    try:
        async with async_driver.session() as session:
            result = await session.run(
                """
                MATCH (m:Movie)-[:BELONGS_TO]->(g:Genre)
                WHERE m.title IN $titles
                WITH m, collect(g.name) AS genres
                WHERE any(genre IN genres WHERE genre IN $sourceGenres)
                RETURN m.title AS title, genres
                """,
                titles=movie_titles, sourceGenres=source_genres
            )
            return [{"title": r["title"], "genres": r["genres"]} async for r in result]
    except Exception as e:
        print(f"⚠️ Neo4j error in filter_by_genre: {e}")
        return []

async def get_user_profile(user_id: str) -> dict:
    """Fetch top genres and directors a user has interacted with."""
    if not async_driver or not user_id:
        return {"genres": [], "directors": []}
    try:
        async with async_driver.session() as session:
            # Top 3 Genres
            genre_res = await session.run("""
                MATCH (u:User {id: $userId})-[r:INTERACTED_WITH]->(m:Movie)-[:BELONGS_TO]->(g:Genre)
                RETURN g.name AS genre, sum(r.count) AS score
                ORDER BY score DESC LIMIT 3
            """, userId=user_id)
            top_genres = [rec["genre"] async for rec in genre_res]

            # Top 3 Directors
            dir_res = await session.run("""
                MATCH (u:User {id: $userId})-[r:INTERACTED_WITH]->(m:Movie)<-[:DIRECTED]-(d:Director)
                RETURN d.name AS director, sum(r.count) AS score
                ORDER BY score DESC LIMIT 3
            """, userId=user_id)
            top_dirs = [rec["director"] async for rec in dir_res]
            
            return {"genres": top_genres, "directors": top_dirs}
    except Exception as e:
        print(f"⚠️ Neo4j user profile error: {e}")
        return {"genres": [], "directors": []}

async def fallback_vector_search(query: str, user_id: str = None) -> str:
    """Fallback: Pure vector search when no specific movie entity is resolved."""
    print("   📐 Fallback: Pure vector search...")
    query_vector = embed_text(query)

    search_results = pinecone_index.query(
        vector=query_vector,
        top_k=8,
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

Your task:
1. If the user's query is completely unrelated to movies or if NONE of these movies are a good match for what the user is looking for, politely reply: "I couldn't find any relevant movies for your query. Please try searching for a different movie, genre, or keyword."
2. Otherwise, pick the top 5 BEST matches.
3. For each pick, explain in a single short sentence WHY it fits (keep explanations very concise).
4. Do NOT mention databases, vectors, or technical terms.
5. Format as a numbered list."""

    try:
        # Note: llm.invoke is blocking, we could use ainvoke if supported, 
        # but for simplicity we keep it as invoke in this context, or await if supported.
        # langchain_google_genai supports ainvoke
        response = await llm.ainvoke([
            {"role": "system", "content": "You are a movie recommendation expert. Respond ONLY with a numbered list of movie recommendations with short explanations, OR politely decline if no movies match. Never respond with JSON."},
            {"role": "user", "content": prompt}
        ])

        answer = response.content
        if isinstance(answer, list):
            answer = " ".join([b.text if hasattr(b, "text") else str(b) for b in answer])
        return answer.strip()
    except Exception as err:
        print(f"⚠️ Vector search LLM invocation failed ({err}). Returning generic error response.")
        return "Sorry, the recommendation engine is currently experiencing high load. Please try again in a few moments."

async def handle_similarity_query(query: str, resolved_entities: dict, user_id: str = None) -> str:
    """Main similarity handler: Pinecone + Neo4j + LLM + Personalization."""
    entities = resolved_entities.get("entities", [])
    movie_entity = next((e for e in entities if e["label"] == "Movie"), None)

    if not movie_entity:
        print("   ⚠️ No movie entity resolved. Falling back to vector search...")
        return await fallback_vector_search(query, user_id)

    movie_name = movie_entity["nodeName"]
    print(f"   🎬 Finding movies similar to: \"{movie_name}\"")

    # Fetch User Profile
    user_profile = await get_user_profile(user_id)
    profile_context = ""
    if user_profile["genres"] or user_profile["directors"]:
        profile_context = f"\nPERSONALIZATION:\nThis user usually likes Genres: {', '.join(user_profile['genres'])} and Directors: {', '.join(user_profile['directors'])}.\nGive a slight boost to movies matching this taste if applicable.\n"

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
    source_genres = await get_movie_genres(movie_name)
    source_themes = await get_movie_themes(movie_name)
    print(f"   ✅ Genres: [{', '.join(source_genres)}]")
    print(f"   ✅ Themes: [{', '.join(source_themes)}]")

    if not source_genres:
        print(f"   ⚠️ No genres found for \"{movie_name}\". Using vector results only.")
        return await fallback_vector_search(query, user_id)

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
    genre_matched = await filter_by_genre(candidate_titles, source_genres)
    print(f"   ✅ {len(genre_matched)} movies share at least one genre")

    if not genre_matched:
        return f"I found movies in the database but none share genres with \"{movie_name}\" ({', '.join(source_genres)}). Try a broader search."

    # Step 6: LLM top 10 selection
    print("   🤖 LLM selecting top 5 (with Personalization)...")
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
{profile_context}
Here are {len(candidate_list)} candidate movies:
{formatted_list}

Pick the 5 BEST matches. Rank by:
1. Genre overlap
2. User Personalization (if applicable)
3. Theme similarity

For each pick, explain in 1-2 sentences WHY it's similar (or how it matches their taste).
Do NOT mention databases, vectors, scores, or technical terms.
Format as a numbered list."""

    try:
        response = await llm.ainvoke([
            {"role": "system", "content": "You are a movie recommendation expert. Respond ONLY with a numbered list of movie recommendations with short explanations. Never respond with JSON."},
            {"role": "user", "content": prompt}
        ])

        answer = response.content
        if isinstance(answer, list):
            answer = " ".join([b.text if hasattr(b, "text") else str(b) for b in answer])
        return answer.strip()
    except Exception as err:
        print(f"⚠️ LLM invocation failed ({err}). Returning generic error response.")
        return "Sorry, the recommendation engine is currently experiencing high load. Please try again in a few moments."
