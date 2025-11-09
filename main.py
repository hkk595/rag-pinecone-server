from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import sys

from config import settings
from services import EmbeddingService, VectorDBService, LLMService
import api.routes as routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    print("=" * 60)
    print("Starting RAG Application")
    print("=" * 60)

    try:
        # Initialize services
        print("\n1. Initializing Embedding Service...")
        routes.embedding_service = EmbeddingService()
        print("   - Embedding Service initialized")

        print("\n2. Initializing Vector DB Service...")
        routes.vector_db_service = VectorDBService()
        print("   - Vector DB Service initialized")

        print("\n3. Connecting to Pinecone index...")
        routes.vector_db_service.initialize_index(dimension=settings.embedding_dimension)
        print("   - Pinecone index ready")

        print("\n4. Initializing LLM Service...")
        routes.llm_service = LLMService()
        print("   - LLM Service initialized")

        # Get index stats
        stats = routes.vector_db_service.get_stats()
        print(f"\n5. Vector Database Stats:")
        print(f"   - Total vectors: {stats['total_vector_count']}")
        print(f"   - Dimension: {stats['dimension']}")
        print(f"   - Index fullness: {stats['index_fullness']:.2%}")

        print("\n" + "=" * 60)
        print("RAG Application started successfully!")
        print("=" * 60)
        print(f"\nAPI Documentation: {settings.service_url}/docs")
        print(f"Health Check: {settings.service_url}/health")
        print("\n")

    except Exception as e:
        print(f"\n✗ Failed to initialize application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    yield

    # Shutdown
    print("\n" + "=" * 60)
    print("Shutting down RAG Application")
    print("=" * 60)


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    import traceback
    print(f"Unhandled exception: {exc}")
    traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc)
        }
    )


# Include routers
app.include_router(routes.router, tags=["RAG"])


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": settings.api_description,
        "endpoints": {
            "docs": "/api/docs",
            "health": "/api/health",
            "query": "/api/query",
            "index": "/api/index",
            "stats": "/api/stats"
        }
    }


if __name__ == "__main__":
    import uvicorn

    print("\nStarting server...")
    print(f"Environment: {settings.pinecone_environment or 'default'}")
    print(f"Index: {settings.pinecone_index_name}")
    print(f"LLM Model: {settings.llm_model}")
    print(f"Embedding Model: {settings.embedding_model}\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
