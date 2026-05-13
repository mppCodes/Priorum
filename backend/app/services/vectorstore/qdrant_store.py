from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_community.vectorstores import Qdrant
from langchain_openai import OpenAIEmbeddings

from app.config import get_settings

settings = get_settings()

QDRANT_COLLECTION = getattr(settings, "qdrant_collection", "priorum_rag")

_client: Optional[QdrantClient] = None
_vectorstore: Optional[Qdrant] = None

def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
        # Crear colección si no existe
        existing = [c.name for c in _client.get_collections().collections]
        if QDRANT_COLLECTION not in existing:
            _client.recreate_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),  # text-embedding-3-small
            )
    return _client

def get_vectorstore() -> Qdrant:
    global _vectorstore
    if _vectorstore is None:
        embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model)
        _vectorstore = Qdrant(
            client=get_qdrant_client(),
            collection_name=QDRANT_COLLECTION,
            embeddings=embeddings,
        )
    return _vectorstore

def upsert_documents(docs: List[Dict[str, Any]]):
    vs = get_vectorstore()
    texts = [d["text"] for d in docs]
    metadatas = [d.get("metadata", {}) for d in docs]
    vs.add_texts(texts=texts, metadatas=metadatas)

def retriever(k: int = 5):
    return get_vectorstore().as_retriever(search_kwargs={"k": k})
