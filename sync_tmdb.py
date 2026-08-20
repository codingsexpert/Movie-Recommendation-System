import os
import requests
import uuid
import time
from dotenv import load_dotenv
from graph_builder import build_graph
from config import pinecone_index, embed_text

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

import random

def fetch_trending_movies(limit=10):
    if not TMDB_API_KEY:
        raise ValueError("TMDB_API_KEY is not set in .env")

    random_page = random.randint(1, 500)
    print(f"🌍 Fetching random popular movies from TMDB (Page {random_page})...")
    
    trending_url = f"{BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&page={random_page}&sort_by=popularity.desc"
    response = requests.get(trending_url)
    response.raise_for_status()
    
    results = response.json().get("results", [])
    random.shuffle(results)
    results = results[:limit]
    
    entities = []
    pinecone_vectors = []
    
    for i, movie_basic in enumerate(results):
        movie_id = movie_basic["id"]
        title = movie_basic.get("title", "")
        print(f"   🎬 [{i+1}/{limit}] Fetching details for: {title}")
        
        detail_url = f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
        detail_res = requests.get(detail_url)
        if detail_res.status_code != 200:
            continue
            
        details = detail_res.json()
        
        # 1. Parse Graph Entity
        release_date = details.get("release_date", "")
        year = int(release_date.split("-")[0]) if release_date else None
        genres = [g["name"] for g in details.get("genres", [])]
        
        credits = details.get("credits", {})
        cast = [c["name"] for c in credits.get("cast", [])[:5]]  # Top 5 actors
        crew = credits.get("crew", [])
        director = next((c["name"] for c in crew if c.get("job") == "Director"), None)
        
        entity = {
            "movie": {"title": title, "year": year},
            "director": {"name": director} if director else {},
            "actors": cast,
            "genres": genres,
            "themes": [], # TMDB does not provide themes directly
            "awards": []
        }
        entities.append(entity)
        
        # 2. Parse Vector Text Chunk
        overview = details.get("overview", "")
        chunk_text = f"Movie Title: {title}\nRelease Year: {year}\nDirector: {director}\nActors: {', '.join(cast)}\nGenres: {', '.join(genres)}\nOverview: {overview}"
        
        try:
            vector = embed_text(chunk_text)
            pinecone_vectors.append({
                "id": f"tmdb-{movie_id}",
                "values": vector,
                "metadata": {"text": chunk_text}
            })
        except Exception as e:
            print(f"   ⚠️ Failed to embed {title}: {e}")
            
        time.sleep(0.1) # Be nice to TMDB rate limits
        
    # Step 3: Insert into Neo4j
    if entities:
        print("\n🗄️  Inserting into Neo4j Knowledge Graph...")
        build_graph(entities)
        
    # Step 4: Insert into Pinecone
    if pinecone_vectors:
        print(f"\n🧠 Upserting {len(pinecone_vectors)} vectors to Pinecone...")
        pinecone_index.upsert(vectors=pinecone_vectors)
        
    print("\n✅ TMDB Sync Complete!")
    return len(entities)

def fetch_and_insert_movie_by_title(title: str) -> str | None:
    """Fetch a specific movie by title from TMDB, insert to Neo4j & Pinecone, and return exact TMDB title."""
    if not TMDB_API_KEY:
        return None

    search_url = f"{BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={title}"
    try:
        res = requests.get(search_url)
        res.raise_for_status()
        results = res.json().get("results", [])
        if not results:
            return None
            
        movie_basic = results[0]
        movie_id = movie_basic["id"]
        tmdb_title = movie_basic.get("title", "")
        
        detail_url = f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
        detail_res = requests.get(detail_url)
        if detail_res.status_code != 200:
            return None
            
        details = detail_res.json()
        release_date = details.get("release_date", "")
        year = int(release_date.split("-")[0]) if release_date else None
        genres = [g["name"] for g in details.get("genres", [])]
        credits = details.get("credits", {})
        cast = [c["name"] for c in credits.get("cast", [])[:5]]
        crew = credits.get("crew", [])
        director = next((c["name"] for c in crew if c.get("job") == "Director"), None)
        
        entity = {
            "movie": {"title": tmdb_title, "year": year},
            "director": {"name": director} if director else {},
            "actors": cast,
            "genres": genres,
            "themes": [],
            "awards": []
        }
        
        overview = details.get("overview", "")
        chunk_text = f"Movie Title: {tmdb_title}\nRelease Year: {year}\nDirector: {director}\nActors: {', '.join(cast)}\nGenres: {', '.join(genres)}\nOverview: {overview}"
        vector = embed_text(chunk_text)
        
        # Insert to Neo4j
        build_graph([entity])
        
        # Upsert to Pinecone
        pinecone_index.upsert(vectors=[{
            "id": f"tmdb-{movie_id}",
            "values": vector,
            "metadata": {"text": chunk_text}
        }])
        
        return tmdb_title
    except Exception as e:
        print(f"⚠️ TMDB fetch failed for '{title}': {e}")
        return None

if __name__ == "__main__":
    fetch_trending_movies()
