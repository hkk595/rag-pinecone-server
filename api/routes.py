from fastapi import APIRouter, HTTPException, status, Depends
import traceback
import time
import logging

from api.models import (
    QueryRequest, QueryResponse, Source,
    IndexRequest, IndexResponse,
    HealthResponse, ServiceStatus,
)
from services import EmbeddingService, VectorDBService, LLMService
from utils.helpers import format_context, prepare_documents_for_indexing
from config.settings import settings

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api")

# Service instances (will be initialized in main.py)
embedding_service: EmbeddingService = None
vector_db_service: VectorDBService = None
llm_service: LLMService = None


def get_embedding_service() -> EmbeddingService:
    """Dependency to get embedding service."""
    if embedding_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service not initialized"
        )
    return embedding_service


def get_vector_db_service() -> VectorDBService:
    """Dependency to get vector DB service."""
    if vector_db_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector DB service not initialized"
        )
    return vector_db_service


def get_llm_service() -> LLMService:
    """Dependency to get LLM service."""
    if llm_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service not initialized"
        )
    return llm_service


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query the RAG system",
    description="Submit a query and receive an AI-generated response based on relevant context from the vector database"
)
async def query(
    request: QueryRequest,
    embedding_svc: EmbeddingService = Depends(get_embedding_service),
    vector_db_svc: VectorDBService = Depends(get_vector_db_service),
    llm_svc: LLMService = Depends(get_llm_service)
):
    """
    Process a user query using the RAG pipeline.

    Steps:
    1. Generate embedding for the query
    2. Search vector database for relevant documents
    3. Format context from retrieved documents
    4. Generate response using LLM with context
    """
    try:
        # Step 1: Generate query embedding
        embedding_start = time.time()
        query_embedding = embedding_svc.generate_embedding(request.query)
        embedding_time = time.time() - embedding_start
        logging.info(f"** Embedding time: {embedding_time:.2f}s")

        # Step 2: Search vector database
        search_start = time.time()
        search_results = vector_db_svc.search(
            query_embedding=query_embedding,
            top_k=request.top_k
        )
        search_time = time.time() - search_start
        logger.info(f"** Search time: {search_time:.2f}s")
        # logger.info(f"Query results:\n{search_results}")

        # Step 3: Format context
        context = format_context(search_results)
        # logger.info(f"Context:\n{context}")

        # Step 4: Generate response
        llm_start = time.time()
        response_text = llm_svc.generate_response(
            query=request.query,
            context=context,
            temperature=request.temperature
        )
        llm_time = time.time() - llm_start
        logger.info(f"** LLM time: {llm_time:.2f}s")

        # Format sources for response
        sources = [
            Source(
                content=result["content"],
                metadata=result["metadata"],
                score=result["score"]
            )
            for result in search_results
        ]

        return QueryResponse(
            response=response_text,
            sources=sources
        )

    except Exception as e:
        print(f"Error processing query: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}"
        )


@router.post(
    "/index",
    response_model=IndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index documents",
    description="Add new documents to the vector database for retrieval"
)
async def index_documents(
    request: IndexRequest,
    embedding_svc: EmbeddingService = Depends(get_embedding_service),
    vector_db_svc: VectorDBService = Depends(get_vector_db_service)
):
    """
    Index documents into the vector database.

    Steps:
    1. Chunk documents if needed
    2. Generate embeddings for all chunks
    3. Upsert to vector database
    """
    try:
        # Prepare documents (chunking and metadata)
        contents = [doc.content for doc in request.documents]
        metadatas = [doc.metadata for doc in request.documents]

        prepared_docs = prepare_documents_for_indexing(
            contents=contents,
            metadatas=metadatas,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap
        )

        # Generate embeddings for all chunks
        texts_to_embed = [doc["content"] for doc in prepared_docs]
        embeddings = embedding_svc.generate_embeddings_batch(texts_to_embed)

        # Prepare documents with embeddings for Pinecone
        documents_with_embeddings = []
        for doc, embedding in zip(prepared_docs, embeddings):
            documents_with_embeddings.append({
                "id": doc["id"],
                "embedding": embedding,
                "metadata": doc["metadata"]
            })

        # Upsert to vector database
        indexed_count = vector_db_svc.upsert_documents(documents_with_embeddings)

        return IndexResponse(
            indexed_count=indexed_count,
            status="success"
        )

    except Exception as e:
        print(f"Error indexing documents: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index documents: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check the health status of the API and its dependencies"
)
async def health_check():
    """
    Check the health of the API and external services.
    """
    services = {}

    # Check Pinecone
    try:
        if vector_db_service and vector_db_service.index:
            stats = vector_db_service.get_stats()
            services["pinecone"] = ServiceStatus(
                status="healthy",
                message=f"Connected. Vectors: {stats['total_vector_count']}"
            )
        else:
            services["pinecone"] = ServiceStatus(
                status="unhealthy",
                message="Index not initialized"
            )
    except Exception as e:
        services["pinecone"] = ServiceStatus(
            status="unhealthy",
            message=str(e)
        )

    # Check OpenAI (embedding)
    try:
        if embedding_service:
            # Try a simple embedding test
            embedding_service.generate_embedding("test")
            services["openai_embeddings"] = ServiceStatus(
                status="healthy",
                message="API responding"
            )
        else:
            services["openai_embeddings"] = ServiceStatus(
                status="unhealthy",
                message="Service not initialized"
            )
    except Exception as e:
        services["openai_embeddings"] = ServiceStatus(
            status="unhealthy",
            message=str(e)
        )

    # Check OpenAI (LLM)
    try:
        if llm_service:
            services["openai_llm"] = ServiceStatus(
                status="healthy",
                message="Service initialized"
            )
        else:
            services["openai_llm"] = ServiceStatus(
                status="unhealthy",
                message="Service not initialized"
            )
    except Exception as e:
        services["openai_llm"] = ServiceStatus(
            status="unhealthy",
            message=str(e)
        )

    # Determine overall health
    overall_status = "healthy" if all(
        s.status == "healthy" for s in services.values()
    ) else "degraded"

    return HealthResponse(
        status=overall_status,
        services=services
    )


@router.get(
    "/stats",
    summary="Get database statistics",
    description="Get statistics about the vector database"
)
async def get_stats(
    vector_db_svc: VectorDBService = Depends(get_vector_db_service)
):
    """Get vector database statistics."""
    try:
        stats = vector_db_svc.get_stats()
        return stats
    except Exception as e:
        print(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )
