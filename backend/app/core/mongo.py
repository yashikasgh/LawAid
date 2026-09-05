from pymongo import MongoClient
import gridfs
from app.core.config import settings

mongo_client = MongoClient(settings.MONGO_URL)
mongo_db = mongo_client.get_default_database()
fs = gridfs.GridFS(mongo_db)