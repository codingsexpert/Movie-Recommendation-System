import os
import json
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import driver, pinecone_index
from graph_handler import handle_graph_query
from similarity_handler import handle_similarity_query
from run_indexing import run_indexing
from tracking_handler import router as tracking_router

app = FastAPI(title="GraphRAG Movie Recommendation Engine")
app.include_router(tracking_router)

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
    userId: str = None

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

    if not driver:
        stats["neo4j"]["status"] = "offline (fallback mode)"
    else:
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
        "poster": "https://image.tmdb.org/t/p/w500/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg",
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
        "backdrop": "https://image.tmdb.org/t/p/w1280/dqAKr27h33d9lXnSpFpQpD4e1Jp.jpg",
        "trailer": "https://www.youtube.com/embed/EXeTwQWrcwY"
    },
    {
        "title": "Oppenheimer", "year": 2023, "rating": 8.9,
        "directors": ["Christopher Nolan"],
        "actors": ["Cillian Murphy", "Emily Blunt", "Matt Damon", "Robert Downey Jr."],
        "genres": ["Biography", "Drama", "History"],
        "themes": ["Atomic Age", "Moral Dilemma", "Manhattan Project"],
        "awards": ["Oscar Winner (7 Academy Awards incl. Best Picture)"],
        "poster": "https://image.tmdb.org/t/p/w500/ptpr0kHGQWukHtIeStLFSVgZsuq.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/rLb2cwF4rACrmioGlacWKVj9FiB.jpg",
        "trailer": "https://www.youtube.com/embed/uYPbbksJxIg"
    },
    {
        "title": "Shutter Island", "year": 2010, "rating": 8.2,
        "directors": ["Martin Scorsese"],
        "actors": ["Leonardo DiCaprio", "Mark Ruffalo", "Ben Kingsley"],
        "genres": ["Mystery", "Thriller", "Psychological"],
        "themes": ["Mental Asylum", "Delusion", "Guilt"],
        "awards": ["National Board of Review Winner"],
        "poster": "https://image.tmdb.org/t/p/w500/4GDy0KVWky9KmLjW3zYc2W6chx.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/vL5LR6VjFXOpA22bNKlYrL8tfv.jpg",
        "trailer": "https://www.youtube.com/embed/5iaYLCiq5RM"
    },
    {
        "title": "The Matrix", "year": 1999, "rating": 8.7,
        "directors": ["Lana Wachowski", "Lilly Wachowski"],
        "actors": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"],
        "genres": ["Sci-Fi", "Action"],
        "themes": ["Simulated Reality", "Cyberpunk", "Free Will"],
        "awards": ["Oscar Winner (4 Academy Awards)"],
        "poster": "https://image.tmdb.org/t/p/w500/f89U3ADGfhBJl6ip1pSUEqBKB0e.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/oYuLEe1hYm1CYjFAbVPIbDEmBwwM.jpg",
        "trailer": "https://www.youtube.com/embed/vKQi3bBA1y8"
    },
    {
        "title": "Dune: Part Two", "year": 2024, "rating": 8.6,
        "directors": ["Denis Villeneuve"],
        "actors": ["Timothée Chalamet", "Zendaya", "Rebecca Ferguson", "Javier Bardem"],
        "genres": ["Sci-Fi", "Adventure", "Action"],
        "themes": ["Prophecy", "Desert Planet", "Empire"],
        "awards": ["Blockbuster Critical Acclaim"],
        "poster": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=600&q=80",
        "backdrop": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=1600&q=80",
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
        "backdrop": "https://image.tmdb.org/t/p/w1280/suqC4lhQwG1A3K340aCYc8u3p2H.jpg",
        "trailer": "https://www.youtube.com/embed/s7EdQ4FqbhY"
    },
    {
        "title": "The Godfather", "year": 1972, "rating": 9.2,
        "directors": ["Francis Ford Coppola"],
        "actors": ["Marlon Brando", "Al Pacino", "James Caan"],
        "genres": ["Crime", "Drama"],
        "themes": ["Family", "Power", "Loyalty"],
        "awards": ["Oscar Winner (Best Picture)"],
        "poster": "https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/tmU7GeKVybMWFButWEGl2M4GeiP.jpg",
        "trailer": "https://www.youtube.com/embed/UaVTIH8mujA"
    },
    {
        "title": "Fight Club", "year": 1999, "rating": 8.8,
        "directors": ["David Fincher"],
        "actors": ["Brad Pitt", "Edward Norton", "Helena Bonham Carter"],
        "genres": ["Drama", "Thriller"],
        "themes": ["Identity", "Consumerism", "Anarchy"],
        "awards": ["Empire Award Winner"],
        "poster": "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/hZkgoQYus5dXo3H8T7Uef6DNknx.jpg",
        "trailer": "https://www.youtube.com/embed/qtRKdVHc-cE"
    },
    {
        "title": "Forrest Gump", "year": 1994, "rating": 8.8,
        "directors": ["Robert Zemeckis"],
        "actors": ["Tom Hanks", "Robin Wright", "Gary Sinise"],
        "genres": ["Drama", "Romance"],
        "themes": ["Destiny", "American History", "Love"],
        "awards": ["Oscar Winner (6 Academy Awards incl. Best Picture)"],
        "poster": "https://image.tmdb.org/t/p/w500/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/7c9UVPPiTPltouxRVY6N9uugaVA.jpg",
        "trailer": "https://www.youtube.com/embed/bLvqoHBptjg"
    },
    {
        "title": "The Shawshank Redemption", "year": 1994, "rating": 9.3,
        "directors": ["Frank Darabont"],
        "actors": ["Tim Robbins", "Morgan Freeman"],
        "genres": ["Drama"],
        "themes": ["Hope", "Freedom", "Injustice"],
        "awards": ["7 Oscar Nominations"],
        "poster": "https://image.tmdb.org/t/p/w500/9cqN021FmmywsP9b6yWvLNx6sXi.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/kXfqcdQKsToO0OUXHcrrNCHDBzO.jpg",
        "trailer": "https://www.youtube.com/embed/PLl99DlL6b4"
    },
    {
        "title": "Gladiator", "year": 2000, "rating": 8.5,
        "directors": ["Ridley Scott"],
        "actors": ["Russell Crowe", "Joaquin Phoenix", "Connie Nielsen"],
        "genres": ["Action", "Drama", "Adventure"],
        "themes": ["Revenge", "Honor", "Roman Empire"],
        "awards": ["Oscar Winner (Best Picture)"],
        "poster": "https://image.tmdb.org/t/p/w500/ty8TGRuvJLPUmAR1H1nRIsgwSmL.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/vE8K87vA6n0e2380fG7G4.jpg",
        "trailer": "https://www.youtube.com/embed/owK1qxDselE"
    },
    {
        "title": "Avengers: Endgame", "year": 2019, "rating": 8.4,
        "directors": ["Anthony Russo", "Joe Russo"],
        "actors": ["Robert Downey Jr.", "Chris Evans", "Scarlett Johansson"],
        "genres": ["Action", "Sci-Fi", "Adventure"],
        "themes": ["Sacrifice", "Time Travel", "Unity"],
        "awards": ["People's Choice Award Winner"],
        "poster": "https://image.tmdb.org/t/p/w500/or06FN3Dka5tukK1e9PBPE3UyOJ.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/7RyHsO4yDXtBv1zUU3mTpHeQ0d5.jpg",
        "trailer": "https://www.youtube.com/embed/TcMBFSGVi1c"
    },
    {
        "title": "Joker", "year": 2019, "rating": 8.4,
        "directors": ["Todd Phillips"],
        "actors": ["Joaquin Phoenix", "Robert De Niro", "Zazie Beetz"],
        "genres": ["Crime", "Drama", "Thriller"],
        "themes": ["Mental Illness", "Society", "Chaos"],
        "awards": ["Oscar Winner (Best Actor)"],
        "poster": "https://image.tmdb.org/t/p/w500/udDclJoHjfjb8Ekgsd4FDteOkCU.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/n6bUvigpRFqSwmPp1m2YMDNq3Fg.jpg",
        "trailer": "https://www.youtube.com/embed/zAGVQLHvwOY"
    },
    {
        "title": "Parasite", "year": 2019, "rating": 8.5,
        "directors": ["Bong Joon-ho"],
        "actors": ["Song Kang-ho", "Lee Sun-kyun", "Cho Yeo-jeong"],
        "genres": ["Drama", "Thriller", "Comedy"],
        "themes": ["Class Divide", "Greed", "Social Commentary"],
        "awards": ["Oscar Winner (Best Picture — first non-English)"],
        "poster": "https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/hiKmpZMGZOSXAAt16Ujwo2lfv1W.jpg",
        "trailer": "https://www.youtube.com/embed/5xH0HfJHsaY"
    },
    {
        "title": "Spider-Man: Across the Spider-Verse", "year": 2023, "rating": 8.7,
        "directors": ["Joaquim Dos Santos", "Kemp Powers"],
        "actors": ["Shameik Moore", "Hailee Steinfeld", "Oscar Isaac"],
        "genres": ["Animation", "Action", "Adventure"],
        "themes": ["Multiverse", "Identity", "Responsibility"],
        "awards": ["Annie Award Winner"],
        "poster": "https://image.tmdb.org/t/p/w500/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/4HodYYKEIsGOdinkGi2Ucz6X9i0.jpg",
        "trailer": "https://www.youtube.com/embed/cqGjhVJWtEg"
    },
    {
        "title": "The Batman", "year": 2022, "rating": 7.8,
        "directors": ["Matt Reeves"],
        "actors": ["Robert Pattinson", "Zoë Kravitz", "Paul Dano", "Colin Farrell"],
        "genres": ["Action", "Crime", "Drama"],
        "themes": ["Vengeance", "Corruption", "Fear"],
        "awards": ["Saturn Award Winner"],
        "poster": "https://image.tmdb.org/t/p/w500/74xTEgt7R36Fpooo50r9T25onhq.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/b0PlSFdDwbyFAJlMR1oAiVSBIwI.jpg",
        "trailer": "https://www.youtube.com/embed/mqqft2x_Aa4"
    },
    {
        "title": "John Wick: Chapter 4", "year": 2023, "rating": 7.7,
        "directors": ["Chad Stahelski"],
        "actors": ["Keanu Reeves", "Donnie Yen", "Bill Skarsgård"],
        "genres": ["Action", "Thriller", "Crime"],
        "themes": ["Survival", "Honor", "Brotherhood"],
        "awards": ["Critics Choice Nomination"],
        "poster": "https://image.tmdb.org/t/p/w500/vZloFAK7NmvMGKE7VKB5dH9FmmC.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/7I6VUdPj6tQECNHdviJkUHD2u89.jpg",
        "trailer": "https://www.youtube.com/embed/qEVUtrk8_B4"
    },
    {
        "title": "Everything Everywhere All at Once", "year": 2022, "rating": 8.0,
        "directors": ["Daniel Kwan", "Daniel Scheinert"],
        "actors": ["Michelle Yeoh", "Ke Huy Quan", "Stephanie Hsu"],
        "genres": ["Action", "Sci-Fi", "Comedy"],
        "themes": ["Multiverse", "Family", "Existentialism"],
        "awards": ["Oscar Winner (7 Academy Awards incl. Best Picture)"],
        "poster": "https://image.tmdb.org/t/p/w500/w3LxiVYdWWRvEVdn5RYq6jIqkb1.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/fWdPrsNzp9FTkPWwP3yjYxnbDvL.jpg",
        "trailer": "https://www.youtube.com/embed/wxN1T1qdQ0I"
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
            user_answer = "**[Warning]** **API Rate Limit Exceeded**: Gemini LLM free tier quota reached for the minute. Please wait 10-15 seconds and try again."
        else:
            user_answer = f"**[Error]** Could not generate quiz match: {err_msg}"
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

from sync_tmdb import fetch_trending_movies

@app.post("/api/sync_tmdb")
def sync_tmdb_endpoint(background_tasks: BackgroundTasks):
    """Trigger background sync of TMDB trending movies."""
    background_tasks.add_task(fetch_trending_movies)
    return {
        "status": "success",
        "message": "TMDB sync launched in background. Trending movies will be added to the Knowledge Graph."
    }

import requests
import os
from fastapi.responses import RedirectResponse

@app.get("/api/poster")
def get_movie_poster(title: str):
    """Fetch movie poster dynamically from TMDB and redirect to image URL."""
    fallback_url = "https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg"
    tmdb_key = os.getenv("TMDB_API_KEY")
    if not tmdb_key:
        return RedirectResponse(url=fallback_url)
        
    try:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_key}&query={title}"
        res = requests.get(url, timeout=3)
        results = res.json().get("results", [])
        if results and results[0].get("poster_path"):
            return RedirectResponse(url=f"https://image.tmdb.org/t/p/w500{results[0]['poster_path']}")
    except Exception:
        pass
        
    return RedirectResponse(url=fallback_url)

from cache_manager import get_cached_response, set_cached_response, generate_cache_key
from intent_resolver import process_query_intent

@app.post("/api/query")
async def process_rag_query(req: QueryRequest):
    """Execute GraphRAG Pipeline and return step-by-step resolution & output."""
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Check Cache First
    cache_key = generate_cache_key("query", text=query.lower())
    cached_data = get_cached_response(cache_key)
    if cached_data:
        print(f"⚡ Cache Hit: '{query}'")
        return cached_data

    try:
        # Phase 1 Unified Call (Halves Latency & Cost)
        classification, resolved = process_query_intent(query)
        
        query_type = classification.get("type", "graph")
        reasoning = classification.get("reasoning", "")

        print(f"\n--- Processing Query: '{query}' ---")
        print(f"   🤖 Intent: {query_type.upper()} ({reasoning})")

        # 3. Route to specific handler
        if query_type == "graph":
            answer = await handle_graph_query(query, resolved)
        else:
            answer = await handle_similarity_query(query, resolved, user_id=req.userId)

        # 4. Fallback formatting if empty
        if not answer:
            answer = "I couldn't find an answer to that right now. Try rephrasing!"

        # 5. Format Output
        response_data = {
            "query": query,
            "classification": classification,
            "resolved_entities": resolved,
            "answer": answer
        }

        # 6. Cache the successful result
        set_cached_response(cache_key, response_data)

        return response_data

    except Exception as e:
        err_msg = str(e)
        import traceback
        traceback.print_exc()
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            user_answer = "**[Warning]** **API Rate Limit Exceeded**: Gemini LLM free tier quota reached. Please wait."
        else:
            user_answer = f"**[Error]** An error occurred processing your request: {err_msg}"
        return {
            "query": query,
            "resolved_entities": {"query": query, "entities": [], "unresolved": []},
            "classification": {"type": "graph", "reasoning": "Error fallback"},
            "answer": user_answer
        }

# Serve static frontend
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
