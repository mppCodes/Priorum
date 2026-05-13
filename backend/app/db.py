from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings

settings = get_settings()

client = AsyncIOMotorClient("mongodb://priorum-mongodb:27017")
db = client.priorum

# Ejemplo: obtener colección
def get_collection(name: str):
    return db[name]