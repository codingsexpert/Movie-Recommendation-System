import json
import hashlib
import redis
from cachetools import TTLCache

# Configure Redis if available, else fallback to in-memory TTL Cache
# TTLCache holds up to 1000 items, expires in 1 hour (3600 seconds)
memory_cache = TTLCache(maxsize=1000, ttl=3600)

REDIS_HOST = "localhost"
REDIS_PORT = 6379

redis_client = None
try:
    # Attempt to connect to local Redis
    temp_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, socket_timeout=1)
    temp_client.ping()
    redis_client = temp_client
    print("✅ Connected to Redis cache")
except redis.ConnectionError:
    print("⚠️ Redis not found. Using fast in-memory TTLCache instead.")
except Exception as e:
    print(f"⚠️ Redis connection failed: {e}. Using fast in-memory TTLCache instead.")

def generate_cache_key(prefix: str, **kwargs) -> str:
    """Generate a deterministic string key from arguments."""
    sorted_items = sorted(kwargs.items())
    key_string = f"{prefix}:" + json.dumps(sorted_items, separators=(",", ":"))
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()

def get_cached_response(key: str):
    """Retrieve data from cache if it exists."""
    if redis_client:
        try:
            cached_data = redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            print(f"Redis get error: {e}")
    else:
        return memory_cache.get(key)
    return None

def set_cached_response(key: str, data: dict, ttl_seconds: int = 3600):
    """Save data to cache."""
    if redis_client:
        try:
            redis_client.setex(key, ttl_seconds, json.dumps(data))
        except Exception as e:
            print(f"Redis set error: {e}")
    else:
        # Note: TTLCache handles TTL automatically at key-level based on initialization
        memory_cache[key] = data
