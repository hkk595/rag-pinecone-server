# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a production-ready Retrieval-Augmented Generation (RAG) application built with FastAPI, Pinecone vector database, and OpenAI. The application provides a REST API for querying a knowledge base using semantic search and AI-generated responses.

**Core flow**: User Query → Generate Embedding → Search Pinecone → Retrieve Context → Generate LLM Response → Return to User

## Development Commands

### Running the Application

```bash
# Start development server (with auto-reload)
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Build image only
docker build -t rag-app .

# Run container
docker run -p 8000:8000 --env-file .env rag-app
```

### Testing

```bash
# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

### Code Formatting

```bash
# Install formatting tools
pip install black isort

# Format code
black .
isort .
```

## Architecture

### Service Layer Pattern

The application uses a three-service architecture initialized at startup via lifespan context manager (main.py:13-66):

1. **EmbeddingService** (`services/embedding_service.py`): Generates vector embeddings using OpenAI's embedding models with retry logic and exponential backoff
2. **VectorDBService** (`services/vector_db_service.py`): Manages Pinecone vector database operations including search, upsert, and index management
3. **LLMService** (`services/llm_service.py`): Generates contextual responses using OpenAI LLM with custom prompt engineering

Services are initialized as module-level variables in `api/routes.py` and injected via FastAPI dependencies for proper error handling.

### Key Design Patterns

**Dependency Injection**: FastAPI dependencies (`get_embedding_service`, `get_vector_db_service`, `get_llm_service`) in `api/routes.py:29-56` ensure services are initialized before handling requests

**Retry Logic**: All external API calls (OpenAI, Pinecone) implement exponential backoff retry mechanism to handle transient failures

**Document Chunking**: Large documents are automatically split into overlapping chunks (`utils/helpers.py:5-59`) to fit embedding model context windows and improve retrieval precision

**Metadata Management**: Vector database stores both embeddings and metadata (source, document_index, chunk_index) for traceability

### Request Flow

**Query Endpoint** (`/api/query`):
1. Generate embedding for user query (`api/routes.py:83`)
2. Search Pinecone for top-k similar vectors (`api/routes.py:86-89`)
3. Format retrieved chunks into context list (`api/routes.py:93`)
4. Generate LLM response with context (`api/routes.py:97-101`)
5. Return response with source attribution (`api/routes.py:113-116`)

**Index Endpoint** (`/api/index`):
1. Chunk documents with overlap (`api/routes.py:152-157`)
2. Generate embeddings in batch (`api/routes.py:161`)
3. Prepare documents with metadata (`api/routes.py:164-170`)
4. Upsert to Pinecone in batches of 100 (`api/routes.py:173`)

### Configuration

All settings are managed through `config/settings.py` using Pydantic's `BaseSettings` which automatically loads from:
- Environment variables
- `.env` file (see `.env.example` for template)

**Critical settings**:
- `embedding_dimension`: Must match OpenAI model (1024 for text-embedding-3-large, 1536 for text-embedding-3-small)
- `pinecone_namespace`: Allows logical separation within same index (default: `__default__`)
- `chunk_size` and `chunk_overlap`: Controls document splitting strategy

### GPT-5 Model Considerations

The codebase includes special handling for GPT-5 (`services/llm_service.py:44-47`):
- Temperature is locked to 1.0 (GPT-5 doesn't support configurable temperature)
- `max_completion_tokens` is set to None to allow unlimited reasoning and output tokens

### Error Handling

- Service initialization failures cause immediate application exit (`main.py:54-58`)
- API errors return structured error responses with appropriate HTTP status codes
- All external API calls have retry logic with exponential backoff
- Health check endpoint (`/api/health`) monitors all service dependencies

## Project Structure

```
rag-pinecone-server/
├── main.py                 # FastAPI app, lifespan management, CORS, exception handlers
├── config/
│   └── settings.py         # Pydantic settings with env var loading
├── services/               # Business logic layer
│   ├── embedding_service.py    # OpenAI embeddings with retry
│   ├── vector_db_service.py    # Pinecone operations
│   └── llm_service.py          # OpenAI LLM with prompt engineering
├── api/
│   ├── models.py          # Pydantic request/response models
│   └── routes.py          # API endpoints with dependency injection
└── utils/
    └── helpers.py         # Document chunking, formatting, ID generation
```

## Common Development Tasks

### Adding New Environment Variables

1. Add to `config/settings.py` as a class attribute
2. Update `.env.example` with example value
3. Reload the application (settings are loaded at startup)

### Modifying LLM Prompts

System and user prompts are in `services/llm_service.py`:
- `_create_system_prompt()`: Defines assistant behavior and guidelines
- `_create_user_prompt()`: Formats query and context for LLM

### Changing Vector Database

The `VectorDBService` abstracts Pinecone operations. To switch to another vector database:
1. Create new service implementing same interface (search, upsert, get_stats)
2. Update initialization in `main.py` lifespan
3. Adjust metadata handling if needed (see `vector_db_service.py:91-101`)

### Namespace Management

The application uses Pinecone namespaces for logical separation. Current namespace: `settings.pinecone_namespace` (default: `__default__`). All operations (search, upsert) automatically use this namespace.

## Important Notes

- The application requires active Pinecone and OpenAI API keys - server will fail to start without them
- Pinecone index is created automatically if it doesn't exist (`vector_db_service.py:32-44`)
- Document IDs are auto-generated as UUIDs - no need to provide them when indexing
- Search results include similarity scores (0-1, where 1 is most similar)
- The health check endpoint makes actual API calls to verify service availability
- CORS is currently set to allow all origins (`main.py:77-83`) - restrict for production
