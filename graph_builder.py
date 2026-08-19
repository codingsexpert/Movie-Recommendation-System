import re
from config import driver

def insert_movie_graph(tx, entity: dict):
    """Insert ONE movie's entities and relationships into Neo4j in a single transaction."""
    movie = entity.get("movie", {})
    director = entity.get("director", {})
    actors = entity.get("actors", [])
    genres = entity.get("genres", [])
    themes = entity.get("themes", [])
    awards = entity.get("awards", [])

    title = movie.get("title")
    year = movie.get("year")
    director_name = director.get("name")

    if not title:
        return

    # Movie node
    tx.run(
        """
        MERGE (m:Movie {title: $title})
        SET m.year = $year
        """,
        title=title, year=year
    )

    # Director node + DIRECTED relationship
    if director_name:
        tx.run(
            """
            MERGE (d:Director {name: $name})
            MERGE (m:Movie {title: $title})
            MERGE (d)-[:DIRECTED]->(m)
            """,
            name=director_name, title=title
        )

    # Actor nodes + ACTED_IN relationships
    for actor_name in actors:
        if actor_name:
            tx.run(
                """
                MERGE (a:Actor {name: $name})
                MERGE (m:Movie {title: $title})
                MERGE (a)-[:ACTED_IN]->(m)
                """,
                name=actor_name, title=title
            )

    # Genre nodes + BELONGS_TO relationships
    for genre_name in genres:
        if genre_name:
            tx.run(
                """
                MERGE (g:Genre {name: $name})
                MERGE (m:Movie {title: $title})
                MERGE (m)-[:BELONGS_TO]->(g)
                """,
                name=genre_name, title=title
            )

    # Theme nodes + EXPLORES relationships
    for theme_name in themes:
        if theme_name:
            tx.run(
                """
                MERGE (t:Theme {name: $name})
                MERGE (m:Movie {title: $title})
                MERGE (m)-[:EXPLORES]->(t)
                """,
                name=theme_name, title=title
            )

    # Award nodes + WON relationships
    for award_name in awards:
        if award_name:
            match = re.match(r"^(.+?)\s*\((.+)\)$", award_name)
            if match:
                award_type = match.group(1).strip()
                category = match.group(2).strip()
                tx.run(
                    """
                    MERGE (aw:Award {name: $award_type, category: $category})
                    MERGE (m:Movie {title: $title})
                    MERGE (m)-[:WON]->(aw)
                    """,
                    award_type=award_type, category=category, title=title
                )

def build_graph(entities: list[dict]):
    """Build complete graph in Neo4j for ALL movies."""
    if not driver:
        print("   ⚠️ Neo4j driver is None. Skipping graph build.")
        return
        
    print(f"\n🔨 Building graph for {len(entities)} movies...\n")

    # Step 1: Create indexes for fast MERGE
    with driver.session() as session:
        session.run("CREATE INDEX IF NOT EXISTS FOR (m:Movie) ON (m.title)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (d:Director) ON (d.name)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (a:Actor) ON (a.name)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (g:Genre) ON (g.name)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (t:Theme) ON (t.name)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (aw:Award) ON (aw.name, aw.category)")
        print("📇 Indexes created.")

    # Step 2: Insert movies one by one
    for i, entity in enumerate(entities):
        with driver.session() as session:
            session.execute_write(insert_movie_graph, entity)
        
        if (i + 1) % 50 == 0 or i == len(entities) - 1:
            print(f"   📊 Inserted {i + 1}/{len(entities)} movies")

    # Step 3: Print stats
    with driver.session() as session:
        node_res = session.run("MATCH (n) RETURN count(n) AS count").single()
        rel_res = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()
        print("\n✅ Graph built!")
        print(f"   Nodes: {node_res['count']}")
        print(f"   Relationships: {rel_res['count']}")
