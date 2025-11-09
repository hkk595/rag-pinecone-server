from pathlib import Path
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from config.settings import settings


class VectorDBService:
    """Service for managing vector database operations with Pinecone."""

    def __init__(self):
        """Initialize Pinecone client and connect to index."""
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        self.namespace = settings.pinecone_namespace
        self.index = None

    def initialize_index(self, dimension: int = 1024) -> None:
        """
        Initialize or connect to a Pinecone index.

        Args:
            dimension: Dimension of the embedding vectors (default 1536 for text-embedding-3-small)

        Raises:
            Exception: If index creation or connection fails
        """
        try:
            # Check if index already exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]

            if self.index_name not in index_names:
                print(f"Creating new Pinecone index: {self.index_name}")
                # Create new index with serverless spec
                self.pc.create_index(
                    name=self.index_name,
                    dimension=dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                print(f"Index '{self.index_name}' created successfully")
            else:
                print(f"Connecting to existing index: {self.index_name}")

            # Connect to the index
            self.index = self.pc.Index(self.index_name)
            print(f"Connected to Pinecone index: {self.index_name}")

        except Exception as e:
            raise Exception(f"Failed to initialize Pinecone index: {e}")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the index.

        Args:
            query_embedding: The query vector
            top_k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of dictionaries containing matched documents with metadata and scores

        Raises:
            Exception: If index is not initialized or search fails
        """
        if self.index is None:
            raise Exception("Index not initialized. Call initialize_index() first.")

        try:
            results = self.index.query(
                namespace=self.namespace,
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                include_values=False,
                filter=filter
            )

            # Format results
            formatted_results = []
            for match in results.matches:
                simple_metadata = match.metadata.copy()
                simple_metadata["filename"] = Path(simple_metadata.get("source", "")).name
                del simple_metadata["source"]
                del simple_metadata["text"]
                formatted_results.append({
                    "id": match.id,
                    "score": match.score,
                    # "content": match.metadata.get("content", ""),
                    "content": match.metadata.get("text", ""),
                    "metadata": simple_metadata
                })

            return formatted_results

        except Exception as e:
            raise Exception(f"Vector search failed: {e}")

    def upsert_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> int:
        """
        Upsert documents with their embeddings to the index.

        Args:
            documents: List of documents, each containing:
                - id: Unique identifier
                - embedding: Vector embedding
                - metadata: Dictionary of metadata (must include 'content')

        Returns:
            Number of documents upserted

        Raises:
            Exception: If index is not initialized or upsert fails
        """
        if self.index is None:
            raise Exception("Index not initialized. Call initialize_index() first.")

        try:
            # Format documents for Pinecone
            vectors = []
            for doc in documents:
                vectors.append({
                    "id": doc["id"],
                    "values": doc["embedding"],
                    "metadata": doc["metadata"]
                })

            # Upsert in batches of 100
            batch_size = 100
            total_upserted = 0

            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
                total_upserted += len(batch)

            print(f"Successfully upserted {total_upserted} documents to Pinecone")
            return total_upserted

        except Exception as e:
            raise Exception(f"Failed to upsert documents: {e}")

    def delete_all(self) -> None:
        """
        Delete all vectors from the index.

        Raises:
            Exception: If index is not initialized or deletion fails
        """
        if self.index is None:
            raise Exception("Index not initialized. Call initialize_index() first.")

        try:
            self.index.delete(delete_all=True)
            print(f"All vectors deleted from index: {self.index_name}")
        except Exception as e:
            raise Exception(f"Failed to delete vectors: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Dictionary containing index statistics

        Raises:
            Exception: If index is not initialized
        """
        if self.index is None:
            raise Exception("Index not initialized. Call initialize_index() first.")

        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness
            }
        except Exception as e:
            raise Exception(f"Failed to get index stats: {e}")
