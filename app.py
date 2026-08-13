import os
import json
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import driver, pinecone_index
from entity_resolver import resolve_query_entities
from query_classifier import classify_query
from graph_handler import handle_graph_query
from similarity_handler import handle_similarity_query
from run_indexing import run_indexing

app = FastAPI(title="GraphRAG Movie Recommendation Engine")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class CypherRequest(BaseModel):
    cypher: str

class QuizRequest(BaseModel):
    mood: str
    genre: str
    era: str

@app.get("/api/stats")
def get_stats():
    """Fetch database status and node/relationship counts."""
    stats = {
        "neo4j": {
            "status": "connected",
            "movies": 0,
            "directors": 0,
            "actors": 0,
            "genres": 0,
            "themes": 0,
            "awards": 0,
            "total_nodes": 0,
            "total_relationships": 0
        },
        "pinecone": {
            "status": "connected",
            "total_vectors": 0
        }
    }

    try:
        with driver.session() as session:
            nodes_res = session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(n) AS cnt
            """)
            for record in nodes_res:
                lbl = record["label"]
                cnt = record["cnt"]
                if lbl == "Movie":
                    stats["neo4j"]["movies"] = cnt
                elif lbl == "Director":
                    stats["neo4j"]["directors"] = cnt
                elif lbl == "Actor":
                    stats["neo4j"]["actors"] = cnt
                elif lbl == "Genre":
                    stats["neo4j"]["genres"] = cnt
                elif lbl == "Theme":
                    stats["neo4j"]["themes"] = cnt
                elif lbl == "Award":
                    stats["neo4j"]["awards"] = cnt

            total_n = session.run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
            total_r = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
            stats["neo4j"]["total_nodes"] = total_n
            stats["neo4j"]["total_relationships"] = total_r
    except Exception as e:
        stats["neo4j"]["status"] = f"error: {str(e)}"

    try:
        if pinecone_index:
            p_stats = pinecone_index.describe_index_stats()
            count = getattr(p_stats, "total_vector_count", getattr(p_stats, "total_record_count", 0))
            stats["pinecone"]["total_vectors"] = count
        else:
            stats["pinecone"]["status"] = "not initialized"
    except Exception as e:
        stats["pinecone"]["status"] = f"error: {str(e)}"

    return stats

FALLBACK_CATALOG = [
    {
        "title": "Inception", "year": 2010, "rating": 8.8,
        "directors": ["Christopher Nolan"],
        "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page", "Tom Hardy"],
        "genres": ["Sci-Fi", "Action", "Thriller"],
        "themes": ["Dreams", "Reality", "Subconscious"],
        "awards": ["Oscar Winner (4 Academy Awards)"],
        "poster": "https://image.tmdb.org/t/p/w500/oYuLE1hYm1CYjFAbVPIbDEmBwwM.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/8ZTVqvKDQ8emSGUEMjsS4yHAiE.jpg",
        "trailer": "https://www.youtube.com/embed/YoHD9XEInc0"
    },
    {
        "title": "Interstellar", "year": 2014, "rating": 8.7,
        "directors": ["Christopher Nolan"],
        "actors": ["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain"],
        "genres": ["Sci-Fi", "Drama", "Adventure"],
        "themes": ["Black Holes", "Time Dilation", "Love & Gravity"],
        "awards": ["Oscar Winner (Best Visual Effects)"],
        "poster": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/xJHokMbljvjADYdit5fKSuV0Sc.jpg",
        "trailer": "https://www.youtube.com/embed/zSWdZVtXT7E"
    },
    {
        "title": "The Dark Knight", "year": 2008, "rating": 9.0,
        "directors": ["Christopher Nolan"],
        "actors": ["Christian Bale", "Heath Ledger", "Aaron Eckhart"],
        "genres": ["Action", "Crime", "Drama"],
        "themes": ["Justice", "Chaos", "Heroism"],
        "awards": ["Oscar Winner (Heath Ledger Best Supporting Actor)"],
        "poster": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/nMK2819TyQvW2guWZ5CS2hZXIw.jpg",
        "trailer": "https://www.youtube.com/embed/EXeTwQWrcwY"
    },
    {
        "title": "Oppenheimer", "year": 2023, "rating": 8.9,
        "directors": ["Christopher Nolan"],
        "actors": ["Cillian Murphy", "Emily Blunt", "Matt Damon", "Robert Downey Jr."],
        "genres": ["Biography", "Drama", "History"],
        "themes": ["Atomic Age", "Moral Dilemma", "Manhattan Project"],
        "awards": ["Oscar Winner (7 Academy Awards incl. Best Picture)"],
        "poster": "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGvC271PqY.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/fm6K8Ofi0Rs2R6hEGUYevjUvy20.jpg",
        "trailer": "https://www.youtube.com/embed/uYPbbksJxIg"
    },
    {
        "title": "Shutter Island", "year": 2010, "rating": 8.2,
        "directors": ["Martin Scorsese"],
        "actors": ["Leonardo DiCaprio", "Mark Ruffalo", "Ben Kingsley"],
        "genres": ["Mystery", "Thriller", "Psychological"],
        "themes": ["Mental Asylum", "Delusion", "Guilt"],
        "awards": ["National Board of Review Winner"],
        "poster": "https://image.tmdb.org/t/p/w500/4BgSWGIpPOmBZGFdMfwFWOf2D9Y.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/w7kWbE2fXbJ4dC41sQhU9o6t0mY.jpg",
        "trailer": "https://www.youtube.com/embed/5iaYLCiq5RM"
    },
    {
        "title": "The Matrix", "year": 1999, "rating": 8.7,
        "directors": ["Lana Wachowski", "Lilly Wachowski"],
        "actors": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"],
        "genres": ["Sci-Fi", "Action"],
        "themes": ["Simulated Reality", "Cyberpunk", "Free Will"],
        "awards": ["Oscar Winner (4 Academy Awards)"],
        "poster": "https://image.tmdb.org/t/p/w500/f89U3w9nYiBAbsfWivHCPOK20d8.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/5v6n6uP3lJ78vK2Cg93W55xW90d.jpg",
        "trailer": "https://www.youtube.com/embed/vKQi3bBA1y8"
    },
    {
        "title": "Dune: Part Two", "year": 2024, "rating": 8.6,
        "directors": ["Denis Villeneuve"],
        "actors": ["Timothée Chalamet", "Zendaya", "Rebecca Ferguson", "Javier Bardem"],
        "genres": ["Sci-Fi", "Adventure", "Action"],
        "themes": ["Prophecy", "Desert Planet", "Empire"],
        "awards": ["Blockbuster Critical Acclaim"],
        "poster": "https://image.tmdb.org/t/p/w500/1pdfLPoLMag8StABMwMvChg7rvi.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/xOM08Go8DFBhidHYxP6yA46UTv8.jpg",
        "trailer": "https://www.youtube.com/embed/Way9Dexny3w"
    },
    {
        "title": "Pulp Fiction", "year": 1994, "rating": 8.9,
        "directors": ["Quentin Tarantino"],
        "actors": ["John Travolta", "Uma Thurman", "Samuel L. Jackson"],
        "genres": ["Crime", "Drama"],
        "themes": ["Non-linear Storytelling", "Redemption", "Los Angeles Underworld"],
        "awards": ["Oscar Winner (Best Screenplay)"],
        "poster": "https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/suaEOtk1N1sgg2MTM7oHO2z83S5.jpg",
        "trailer": "https://www.youtube.com/embed/s7EdQ4FqbhY"
    }
]

@app.get("/api/all_movies")
def get_all_movies():
    """Fetch list of all movie titles for selector dropdowns."""
    if driver:
        try:
            with driver.session() as session:
                res = session.run("MATCH (m:Movie) RETURN coalesce(m.title, m.name) AS title ORDER BY title ASC")
                titles = [r["title"] for r in res if r["title"]]
                if titles:
                    return titles
        except Exception:
            pass
    return [m["title"] for m in FALLBACK_CATALOG]

@app.get("/api/catalog")
def get_catalog_movies():
    """Fetch full rich movie cards list for the streaming catalog UI."""
    if driver:
        try:
            with driver.session() as session:
                res = session.run("""
                    MATCH (m:Movie)
                    OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
                    OPTIONAL MATCH (a:Actor)-[:ACTED_IN]->(m)
                    OPTIONAL MATCH (m)-[:BELONGS_TO]->(g:Genre)
                    OPTIONAL MATCH (m)-[:EXPLORES]->(t:Theme)
                    OPTIONAL MATCH (m)-[:WON]->(aw:Award)
                    RETURN coalesce(m.title, m.name) AS title, m.year AS year,
                           collect(DISTINCT d.name) AS directors,
                           collect(DISTINCT a.name) AS actors,
                           collect(DISTINCT g.name) AS genres,
                           collect(DISTINCT t.name) AS themes,
                           collect(DISTINCT aw.name) AS awards
                    ORDER BY m.year DESC, title ASC
                """)
                movies = []
                for r in res:
                    if r["title"]:
                        movie_dict = dict(r)
                        matching_fb = next((f for f in FALLBACK_CATALOG if f["title"].lower() == movie_dict["title"].lower()), None)
                        if matching_fb:
                            movie_dict["poster"] = matching_fb.get("poster")
                            movie_dict["backdrop"] = matching_fb.get("backdrop")
                            movie_dict["rating"] = matching_fb.get("rating")
                            movie_dict["trailer"] = matching_fb.get("trailer")
                        movies.append(movie_dict)
                if movies:
                    return movies
        except Exception as e:
            print(f"⚠️ Neo4j catalog query error ({e}), using fallback catalog")

    return FALLBACK_CATALOG


@app.get("/api/movie/{title}")
def get_movie_details(title: str):
    """Fetch full details for a single movie from Neo4j."""
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (m:Movie)
                WHERE toLower(m.title) = toLower($title)
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
                       collect(DISTINCT aw.name) AS awards
            """, title=title)
            record = result.single()
            if not record or not record["title"]:
                raise HTTPException(status_code=404, detail="Movie not found")
            return dict(record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compare")
def compare_movies(movie1: str, movie2: str):
    """Compare two movies side-by-side using Neo4j graph data."""
    try:
        m1_details = get_movie_details(movie1)
        m2_details = get_movie_details(movie2)

        shared_directors = list(set(m1_details["directors"]).intersection(set(m2_details["directors"])))
        shared_actors = list(set(m1_details["actors"]).intersection(set(m2_details["actors"])))
        shared_genres = list(set(m1_details["genres"]).intersection(set(m2_details["genres"])))
        shared_themes = list(set(m1_details["themes"]).intersection(set(m2_details["themes"])))
        shared_awards = list(set(m1_details["awards"]).intersection(set(m2_details["awards"])))

        return {
            "movie1": m1_details,
            "movie2": m2_details,
            "shared": {
                "directors": shared_directors,
                "actors": shared_actors,
                "genres": shared_genres,
                "themes": shared_themes,
                "awards": shared_awards
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph_subnetwork/{entity_name}")
def get_graph_subnetwork(entity_name: str):
    """Fetch nodes and relationships around entity for 2D Graph Visualizer."""
    try:
        nodes = []
        edges = []
        node_ids = set()

        with driver.session() as session:
            res = session.run("""
                MATCH (n)
                WHERE toLower(coalesce(n.title, n.name)) CONTAINS toLower($name)
                WITH n LIMIT 1
                MATCH path = (n)-[r]-(m)
                RETURN n, r, m
                LIMIT 12
            """, name=entity_name)

            for record in res:
                source_node = record["n"]
                target_node = record["m"]
                rel = record["r"]

                for node in [source_node, target_node]:
                    label = list(node.labels)[0] if node.labels else "Unknown"
                    name = node.get("title") or node.get("name") or "Unnamed"
                    nid = f"{label}:{name}"

                    if nid not in node_ids:
                        node_ids.add(nid)
                        nodes.append({
                            "id": nid,
                            "label": name,
                            "group": label
                        })

                s_label = list(source_node.labels)[0] if source_node.labels else "Unknown"
                s_name = source_node.get("title") or source_node.get("name")
                t_label = list(target_node.labels)[0] if target_node.labels else "Unknown"
                t_name = target_node.get("title") or target_node.get("name")

                edges.append({
                    "from": f"{s_label}:{s_name}",
                    "to": f"{t_label}:{t_name}",
                    "label": rel.type
                })

        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}

@app.post("/api/run_cypher")
def run_custom_cypher(req: CypherRequest):
    """Developer Cypher Playground endpoint: execute read-only Cypher query."""
    cypher = req.cypher.strip()
    if not cypher:
        raise HTTPException(status_code=400, detail="Cypher query cannot be empty.")
    if any(kw in cypher.upper() for kw in ["DELETE", "DETACH", "CREATE", "SET", "DROP"]):
        raise HTTPException(status_code=400, detail="Only read-only MATCH/RETURN queries are allowed.")

    try:
        with driver.session() as session:
            res = session.run(cypher)
            records = [dict(record) for record in res]
            return {"count": len(records), "records": records[:50]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/movie_match_quiz")
def process_movie_quiz(req: QuizRequest):
    """Personalized 3-question Movie Match Quiz."""
    try:
        synthetic_query = f"Recommend a top {req.genre} movie matching mood '{req.mood}' from era '{req.era}'"
        resolved = resolve_query_entities(synthetic_query)
        answer = handle_similarity_query(synthetic_query, resolved)
        return {
            "quiz_params": {"mood": req.mood, "genre": req.genre, "era": req.era},
            "recommendation": answer
        }
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            user_answer = "⚠️ **API Rate Limit Exceeded**: Gemini LLM free tier quota reached for the minute. Please wait 10-15 seconds and try again."
        else:
            user_answer = f"⚠️ Could not generate quiz match: {err_msg}"
        return {
            "quiz_params": {"mood": req.mood, "genre": req.genre, "era": req.era},
            "recommendation": user_answer
        }

@app.post("/api/upload_pdf")
def upload_and_index_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload new PDF and index into Neo4j & Pinecone in background."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    os.makedirs("./data/uploads", exist_ok=True)
    file_path = f"./data/uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(run_indexing, file_path)

    return {
        "status": "success",
        "message": f"File '{file.filename}' uploaded successfully. Graph & Vector indexing launched in background.",
        "file_path": file_path
    }

@app.post("/api/query")
def process_rag_query(req: QueryRequest):
    """Execute GraphRAG Pipeline and return step-by-step resolution & output."""
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        resolved = resolve_query_entities(query)
        classification = classify_query(query, resolved)
        query_type = classification.get("type", "graph")
        reasoning = classification.get("reasoning", "")

        if query_type == "similarity":
            answer = handle_similarity_query(query, resolved)
        else:
            answer = handle_graph_query(query, resolved)

        return {
            "query": query,
            "resolved": resolved,
            "classification": {
                "type": query_type,
                "reasoning": reasoning
            },
            "answer": answer
        }
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            user_answer = "⚠️ **API Rate Limit Exceeded**: Gemini LLM free tier quota reached for the minute. Please wait 10-15 seconds and click **Execute Query** again."
        else:
            user_answer = f"⚠️ An error occurred processing your request: {err_msg}"

        return {
            "query": query,
            "resolved": {"query": query, "entities": [], "unresolved": []},
            "classification": {"type": "graph", "reasoning": "Error fallback"},
            "answer": user_answer
        }

# Serve static frontend
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
