"""mongo.py — MongoDB/GridFS connection for LawAid file storage.

MongoDB is OPTIONAL for local development. When unavailable, endpoints that
depend on file storage will return a clear HTTP 503 error rather than a
fake/dummy file ID.

Check `mongo_available` before attempting fs.put() / fs.get() calls.
"""

from pymongo import MongoClient
import gridfs
from app.core.config import settings

mongo_available: bool = False
mongo_client = None
mongo_db = None
fs = None

try:
    _client = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)
    # Force a real connection attempt to check availability
    _client.server_info()
    _db = _client.get_default_database()
    _fs = gridfs.GridFS(_db)

    mongo_client = _client
    mongo_db = _db
    fs = _fs
    mongo_available = True
    print("[MONGODB] Connected successfully.")

except Exception as _mongo_err:
    print(f"[MONGODB WARNING] Could not connect to MongoDB - file storage (GridFS) is UNAVAILABLE.")
    print(f"  Endpoints requiring file storage will return HTTP 503 until MongoDB is running.")
    print(f"  Configured URL: {settings.MONGO_URL}")
