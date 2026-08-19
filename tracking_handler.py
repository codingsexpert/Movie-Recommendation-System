from fastapi import APIRouter
from pydantic import BaseModel
from config import driver
import time

router = APIRouter()

class TrackEventRequest(BaseModel):
    userId: str
    eventType: str # "movie_click", "search", "similar_click"
    targetId: str
    targetName: str # e.g. "Inception" or query string

@router.post("/api/track")
def track_user_event(req: TrackEventRequest):
    """Log a user action to Neo4j to build a personalization profile."""
    if not driver:
        return {"status": "ignored", "reason": "No DB connection"}
    
    try:
        with driver.session() as session:
            # Ensure User node exists
            session.run("MERGE (u:User {id: $userId})", userId=req.userId)

            if req.eventType == "movie_click" or req.eventType == "similar_click":
                # Link User to Movie they viewed/interacted with
                session.run("""
                    MATCH (u:User {id: $userId})
                    MATCH (m:Movie) WHERE toLower(m.title) = toLower($targetName)
                    MERGE (u)-[r:INTERACTED_WITH]->(m)
                    SET r.count = coalesce(r.count, 0) + 1, r.last_interaction = timestamp(), r.type = $eventType
                """, userId=req.userId, targetName=req.targetName, eventType=req.eventType)
                print(f"📈 Tracked: User {req.userId} -> {req.eventType} -> {req.targetName}")
                
            elif req.eventType == "search":
                # Link User to Search Query
                session.run("""
                    MATCH (u:User {id: $userId})
                    MERGE (q:SearchQuery {query: $targetName})
                    MERGE (u)-[r:SEARCHED]->(q)
                    SET r.count = coalesce(r.count, 0) + 1, r.last_searched = timestamp()
                """, userId=req.userId, targetName=req.targetName)
                print(f"📈 Tracked: User {req.userId} -> search -> {req.targetName}")

        return {"status": "success"}
    except Exception as e:
        print(f"⚠️ Tracking error: {e}")
        return {"status": "error", "message": str(e)}
