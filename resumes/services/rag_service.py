import hashlib
import uuid

import chromadb
import requests
from django.conf import settings


class RAGService:

    @staticmethod
    def get_client():
        return chromadb.PersistentClient(
            path=str(settings.RAG_PERSIST_DIR)
        )

    @classmethod
    def get_collection(cls):
        client = cls.get_client()

        return client.get_or_create_collection(
            name=settings.RAG_COLLECTION_NAME,
            metadata={
                "description": "AI Recruitment Platform RAG knowledge base"
            },
        )

    @staticmethod
    def make_doc_id(record_type, record_id, chunk_index=0):
        raw = f"{record_type}:{record_id}:{chunk_index}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def chunk_text(text, chunk_size=1200, overlap=150):
        if not text:
            return []

        text = str(text).strip()

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            start = end - overlap

            if start < 0:
                start = 0

            if start >= len(text):
                break

        return chunks

    @staticmethod
    def embed_text(text):
        url = settings.OLLAMA_BASE_URL.rstrip("/") + "/api/embeddings"

        payload = {
            "model": settings.OLLAMA_EMBED_MODEL,
            "prompt": text,
        }

        response = requests.post(
            url,
            json=payload,
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        embedding = data.get("embedding")

        if not embedding:
            raise ValueError("Ollama did not return embedding.")

        return embedding

    @classmethod
    def upsert_record(cls, record_type, record_id, text, metadata=None):
        metadata = metadata or {}

        collection = cls.get_collection()

        chunks = cls.chunk_text(text)

        if not chunks:
            return {
                "success": False,
                "message": "No text to index.",
            }

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for index, chunk in enumerate(chunks):
            doc_id = cls.make_doc_id(
                record_type=record_type,
                record_id=record_id,
                chunk_index=index,
            )

            chunk_metadata = {
                "record_type": record_type,
                "record_id": str(record_id),
                "chunk_index": index,
            }

            for key, value in metadata.items():
                if value is None:
                    value = ""

                chunk_metadata[key] = str(value)

            ids.append(doc_id)
            documents.append(chunk)
            metadatas.append(chunk_metadata)
            embeddings.append(cls.embed_text(chunk))

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        return {
            "success": True,
            "record_type": record_type,
            "record_id": record_id,
            "chunks": len(chunks),
        }

    @classmethod
    def delete_record(cls, record_type, record_id):
        collection = cls.get_collection()

        record_id = str(record_id)

        existing = collection.get(
            where={
                "$and": [
                    {"record_type": record_type},
                    {"record_id": record_id},
                ]
            }
        )

        ids = existing.get("ids", [])

        if ids:
            collection.delete(ids=ids)

        return {
            "success": True,
            "deleted": len(ids),
        }

    @classmethod
    def search(cls, query, user, top_k=8):
        collection = cls.get_collection()

        query_embedding = cls.embed_text(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=40,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        final_results = []

        for document, metadata, distance in zip(documents, metadatas, distances):
            if cls.user_can_access_metadata(user, metadata):
                final_results.append(
                    {
                        "content": document,
                        "metadata": metadata,
                        "distance": distance,
                    }
                )

            if len(final_results) >= top_k:
                break

        return final_results

    @staticmethod
    def user_can_access_metadata(user, metadata):
        if user.is_staff:
            return True

        record_type = metadata.get("record_type")

        profile = getattr(user, "profile", None)
        role = getattr(profile, "role", "")

        user_id = str(user.id)

        if record_type == "job_post":
            return metadata.get("status") == "open"

        if record_type == "company_profile":
            return metadata.get("recruiter_status") == "approved"

        if record_type == "resume":
            return metadata.get("owner_id") == user_id

        if record_type == "job_application":
            if metadata.get("applicant_id") == user_id:
                return True

            if role == "recruiter" and metadata.get("job_recruiter_id") == user_id:
                return True

        if record_type == "recruiter_job":
            if role == "recruiter" and metadata.get("recruiter_id") == user_id:
                return True

        return False