# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A production-ready RAG (Retrieval-Augmented Generation) application built with FastAPI, Pinecone vector database, and OpenAI. The system indexes documents, performs semantic search using embeddings, and generates context-aware responses.

## Development Commands

### Running the Application

```bash
# Start the server (recommended)
python main.py

# Alternative: using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server runs on `http://localhost:8000` with interactive API docs at `/docs`.

### Testing

```bash
# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_file.py

# Run with verbose output
pytest -v tests/
```

### Code Formatting

```bash
# Install formatting tools
pip install black isort

# Format all code
black .
isort .
```

### Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy example environment file
cp .env.example .env
# Then edit .env with your API keys
```

### Docker

```bash
# Build the Docker image
docker build -t rag-app:latest .

# Run the container (with environment variables from .env file)
docker run -d \
  --name rag-app \
  -p 8000:8000 \
  --env-file .env \
  rag-app:latest

# Run interactively (see logs in real-time)
docker run -it \
  --name rag-app \
  -p 8000:8000 \
  --env-file .env \
  rag-app:latest

# View logs
docker logs rag-app

# View logs in real-time
docker logs -f rag-app

# Stop the container
docker stop rag-app

# Remove the container
docker rm rag-app

# Execute commands inside running container
docker exec -it rag-app bash

# Build and run with custom tag
docker build -t rag-app:v1.0 .
docker run -d --name rag-app -p 8000:8000 --env-file .env rag-app:v1.0

# Using Docker Compose (recommended for easier management)
docker-compose up -d          # Build and run in detached mode
docker-compose up             # Run with logs visible
docker-compose down           # Stop and remove containers
docker-compose logs -f        # View logs in real-time
docker-compose restart        # Restart the service
docker-compose build          # Rebuild the image
```

**Docker Notes:**
- The container runs as a non-root user (appuser) for security
- Health check runs every 30s, hitting `/api/health` endpoint
- Requires `.env` file with API keys (use `--env-file .env` or individual `-e` flags)
- Port 8000 is exposed by default
- The image uses Python 3.12-slim for smaller size
- Docker Compose simplifies running with `docker-compose up -d`

### AWS Lambda Deployment

Deploy the application to AWS Lambda with API Gateway using the automated deployment script:

```bash
# Prerequisites:
# 1. Install and configure AWS CLI: aws configure
# 2. Ensure Docker is running
# 3. Create .env file with your API keys

# Deploy with default settings (us-east-1, 2GB memory, 300s timeout)
./deploy-lambda.sh

# Deploy with custom configuration
./deploy-lambda.sh \
  --region us-west-2 \
  --function-name my-rag-app \
  --memory 3008 \
  --timeout 900

# View deployment options
./deploy-lambda.sh --help
```

**What the deployment script does:**

1. **Creates ECR Repository**: Sets up AWS Elastic Container Registry for your Docker images
2. **Builds Lambda Image**: Uses `Dockerfile.lambda` with AWS Lambda Web Adapter
3. **Pushes to ECR**: Uploads the Docker image to your private registry
4. **Creates/Updates Lambda Function**: Deploys function with your environment variables
5. **Sets up IAM Role**: Creates execution role with necessary permissions
6. **Configures API Gateway**: Creates HTTP API Gateway pointing to your Lambda function
7. **Sets Permissions**: Allows API Gateway to invoke your Lambda function

**Lambda Configuration:**

- **Memory**: 2048 MB (default) - increase for better performance
- **Timeout**: 300 seconds (5 minutes) - Lambda max is 900 seconds (15 minutes)
- **Environment Variables**: Automatically loaded from `.env` file
- **Runtime**: Container image with AWS Lambda Web Adapter
- **Cold Start**: First request may take 10-30 seconds, subsequent requests are faster

**After Deployment:**

```bash
# Test the deployed API
curl https://YOUR_API_ID.execute-api.REGION.amazonaws.com/api/health

# View Lambda logs in real-time
aws logs tail /aws/lambda/rag-app --follow --region us-east-1

# Update the function (after code changes)
./deploy-lambda.sh  # Re-run the script

# Delete the deployment
aws lambda delete-function --function-name rag-app --region us-east-1
aws ecr delete-repository --repository-name rag-app --force --region us-east-1
aws apigatewayv2 delete-api --api-id YOUR_API_ID --region us-east-1
```

**Lambda vs Traditional Deployment:**

- **Lambda**: Serverless, pay per request, auto-scaling, AWS managed
  - Use `Dockerfile.lambda` with AWS Lambda Web Adapter
  - Best for variable/unpredictable traffic
  - Cold start latency on first request

- **Traditional (ECS/EC2/Docker)**: Always-on container
  - Use standard `Dockerfile`
  - Best for consistent traffic
  - No cold starts

**Important Lambda Notes:**

- Pinecone and OpenAI connections are established on each cold start
- Consider using Lambda provisioned concurrency to reduce cold starts
- Lambda execution time is limited to 15 minutes maximum
- Embedding dimension must be set correctly before deployment (cannot change Pinecone index structure easily)
- Environment variables are encrypted at rest in Lambda

## Architecture

### Service Layer Pattern

The application uses a three-tier service architecture with dependency injection:

1. **Service Initialization** (`main.py`): Services are initialized once during application startup in the `lifespan()` context manager, then injected into route handlers as global instances via `api.routes` module.

2. **Three Core Services**:
   - `EmbeddingService` (`services/embedding_service.py`): Generates text embeddings using OpenAI API
   - `VectorDBService` (`services/vector_db_service.py`): Manages Pinecone vector database operations
   - `LLMService` (`services/llm_service.py`): Generates responses using OpenAI LLM

3. **API Routes** (`api/routes.py`): Route handlers use FastAPI dependency injection via `Depends()` to access services. Service instances are stored as module-level variables initialized during startup.

### RAG Pipeline Flow

Query Processing (`POST /query`):
1. Generate embedding for user query → `EmbeddingService.generate_embedding()`
2. Search vector DB for similar documents → `VectorDBService.search()`
3. Format retrieved documents as context → `utils.helpers.format_context()`
4. Generate LLM response with context → `LLMService.generate_response()`

Document Indexing (`POST /index`):
1. Chunk documents with overlap → `utils.helpers.prepare_documents_for_indexing()`
2. Generate embeddings in batch → `EmbeddingService.generate_embeddings_batch()`
3. Upsert vectors to Pinecone → `VectorDBService.upsert_documents()`

### Configuration Management

All configuration is centralized in `config/settings.py` using Pydantic settings:
- Loads from `.env` file automatically
- Type-safe with validation
- Access via singleton: `from config.settings import settings`

Critical settings:
- `embedding_dimension`: Must match Pinecone index dimension (default: 1024 for text-embedding-3-large)
- `llm_model`: Currently configured for GPT-5 (has specific handling in code)
- `chunk_size` and `chunk_overlap`: Control document chunking behavior

### GPT-5 Specific Handling

The codebase has special logic for GPT-5 in `services/llm_service.py`:
- Temperature is hardcoded to 1 (GPT-5 doesn't support configurable temperature)
- `max_completion_tokens` is set to `None` (no token limit)
- Uses `developer` role instead of `system` role for prompts

When modifying LLM code, check if the model is GPT-5 before applying settings.

### Document Processing

Documents are chunked using character-based splitting with intelligent boundary detection:
- Chunks respect sentence boundaries (`.`, `!`, `?`) when possible
- Falls back to word boundaries (spaces) if no sentence boundary found
- Each chunk includes metadata: `document_index`, `chunk_index`, `total_chunks`
- Metadata includes a `content` field that duplicates the chunk text (required by Pinecone schema)

### Error Handling

All service methods implement retry logic with exponential backoff:
- Default: 3 retries with 1 second initial delay
- Doubles wait time on each retry (1s, 2s, 4s)
- Used in: embedding generation, LLM calls

Routes return structured HTTP exceptions with appropriate status codes.

### API Route Structure

Routes are defined in `api/routes.py` with `/api` prefix:
- Actual endpoints: `/api/query`, `/api/index`, `/api/health`, `/api/stats`
- All use Pydantic models from `api/models.py` for request/response validation
- Service dependencies are injected via FastAPI's `Depends()` mechanism

### Metadata Schema

When indexing documents in Pinecone, metadata must include:
- `text`: The actual document content (Pinecone stores this, not the vector)
- `source`: File path or document identifier (gets converted to `filename` in responses)
- Custom fields: Can add any additional metadata (e.g., `author`, `topic`)

In search results, the service:
- Extracts `text` field as `content` in response
- Converts `source` path to just filename
- Removes `source` and `text` from returned metadata to keep it clean

## Key Implementation Details

### Service Initialization Order

Services MUST be initialized in this order (enforced in `main.py`):
1. `EmbeddingService` (no dependencies)
2. `VectorDBService` (no dependencies)
3. `VectorDBService.initialize_index()` (must happen before first use)
4. `LLMService` (no dependencies)

The index initialization requires the embedding dimension from settings.

### Pinecone Index Management

- Index name and host are configured in settings
- Uses serverless spec (AWS, us-east-1)
- Metric: cosine similarity
- If index doesn't exist, it's created automatically
- Namespace: `__default__` (configurable via settings)

### Dependencies

Core libraries (see `requirements.txt`):
- `fastapi==0.121.0`: Web framework
- `uvicorn[standard]==0.38.0`: ASGI server
- `pinecone[grpc]==7.3.0`: Vector database client
- `openai==2.7.1`: OpenAI API client
- `pydantic==2.12.4`: Data validation
- `pydantic-settings==2.11.0`: Settings management

## Common Patterns

### Adding a New Endpoint

1. Define request/response models in `api/models.py`
2. Add route handler in `api/routes.py` with proper decorators
3. Use `Depends()` to inject required services
4. Follow existing error handling patterns

### Modifying Service Behavior

Services are stateless except for API clients. To modify:
1. Update the service class method
2. If adding new settings, add to `config/settings.py` and `.env.example`
3. Update retry logic if calling external APIs

### Working with Embeddings

- Batch operations are more efficient: use `generate_embeddings_batch()` when indexing multiple documents
- Single embeddings: use `generate_embedding()` for queries
- Dimension must match between embedding generation and Pinecone index

## API Testing Examples

```bash
# Health check
curl http://localhost:8000/api/health

# Query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?", "top_k": 3}'

# Index documents
curl -X POST http://localhost:8000/api/index \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [{
      "content": "Machine learning is...",
      "metadata": {"source": "ml_guide.txt"}
    }]
  }'

# Get stats
curl http://localhost:8000/api/stats
```
