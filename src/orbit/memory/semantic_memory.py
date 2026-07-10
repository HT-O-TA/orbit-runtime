from typing import List, Dict, Optional
from abc import ABC, abstractmethod


class SemanticMemory(ABC):
    @abstractmethod
    async def add_document(self, document_id: str, content: str, metadata: Optional[Dict[str, str]] = None) -> None:
        pass

    @abstractmethod
    async def retrieve_documents(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> None:
        pass

    @abstractmethod
    async def search(self, query: str, filters: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
        pass


class InMemorySemanticMemory(SemanticMemory):
    def __init__(self):
        self.documents: Dict[str, Dict[str, str]] = {}

    async def add_document(self, document_id: str, content: str, metadata: Optional[Dict[str, str]] = None) -> None:
        self.documents[document_id] = {
            "content": content,
            "metadata": metadata or {},
        }

    async def retrieve_documents(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        results = []
        for doc_id, doc_data in self.documents.items():
            if query.lower() in doc_data["content"].lower():
                results.append({
                    "document_id": doc_id,
                    "content": doc_data["content"],
                    **doc_data["metadata"],
                })
        return results[:top_k]

    async def delete_document(self, document_id: str) -> None:
        if document_id in self.documents:
            del self.documents[document_id]

    async def search(self, query: str, filters: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
        results = await self.retrieve_documents(query)
        if filters:
            results = [
                doc for doc in results
                if all(doc.get(k) == v for k, v in filters.items())
            ]
        return results
