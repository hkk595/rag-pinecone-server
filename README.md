# rag-pinecone-server

A production-ready Retrieval-Augmented Generation (RAG) application built with FastAPI, Pinecone, and OpenAI. This application allows you to query a knowledge base through a REST API, retrieving relevant context and generating informed responses.

## Features

- **Vector Search**: Store and search documents using Pinecone vector database
- **Semantic Search**: Use OpenAI embeddings for semantic similarity search
- **AI-Powered Responses**: Generate contextual responses with OpenAI GPT models
- **REST API**: Clean and documented FastAPI endpoints
- **Document Management**: Index and manage documents with automatic chunking
- **Health Monitoring**: Built-in health checks and statistics endpoints
- **Error Handling**: Robust error handling with automatic retries

## Architecture

```
User Query → FastAPI → Generate Embedding → Search Pinecone → Retrieve Context → Generate Response → Return to User
```

## Prerequisites

- Python 3.9 or higher
- OpenAI API account with API key
- Pinecone account with API key
- pip and virtualenv

## Installation

### 1. Clone the Repository

```bash
cd /home/kkho/Development/ml_lab/rag_demo
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Linux/Mac
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=your-pinecone-environment-here
PINECONE_INDEX_NAME=rag-demo
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
TOP_K_RESULTS=5
```

#### Getting API Keys

**OpenAI API Key:**
1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Create a new API key
4. Copy the key to your `.env` file

**Pinecone API Key:**
1. Go to https://www.pinecone.io/
2. Sign up for a free account
3. Navigate to API Keys in the console
4. Copy your API key and environment to `.env` file

## Running the Application

### Start the Server

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

### Access the API Documentation

Once the server is running, visit:
- **Interactive API docs**: http://localhost:8000/api/docs
- **Alternative docs**: http://localhost:8000/api/redoc
- **Health check**: http://localhost:8000/api/health

## API Endpoints

### 1. Query Endpoint

Submit a query and get an AI-generated response based on relevant context.

**Endpoint**: `POST /query`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "top_k": 5,
    "temperature": 0.7
  }'
```

**Request Body**:
```json
{
  "query": "Your question here",
  "top_k": 5,
  "temperature": 0.7
}
```

**Response**:
```json
{
  "response": "AI-generated answer based on context...",
  "sources": [
    {
      "content": "Relevant document content...",
      "metadata": {"source": "doc1.txt"},
      "score": 0.95
    }
  ]
}
```

### 2. Index Documents Endpoint

Add new documents to the vector database.

**Endpoint**: `POST /index`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/index" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "content": "Machine learning is a subset of artificial intelligence...",
        "metadata": {"source": "ml_guide.txt", "author": "John Doe"}
      },
      {
        "content": "Deep learning uses neural networks with multiple layers...",
        "metadata": {"source": "dl_intro.txt", "author": "Jane Smith"}
      }
    ]
  }'
```

**Response**:
```json
{
  "indexed_count": 2,
  "status": "success"
}
```

### 3. Health Check Endpoint

Check the health status of the API and its dependencies.

**Endpoint**: `GET /health`

**Request**:
```bash
curl "http://localhost:8000/api/health"
```

**Response**:
```json
{
  "status": "healthy",
  "services": {
    "pinecone": {
      "status": "healthy",
      "message": "Connected. Vectors: 150"
    },
    "openai_embeddings": {
      "status": "healthy",
      "message": "API responding"
    },
    "openai_llm": {
      "status": "healthy",
      "message": "Service initialized"
    }
  }
}
```

### 4. Statistics Endpoint

Get vector database statistics.

**Endpoint**: `GET /stats`

**Request**:
```bash
curl "http://localhost:8000/api/stats"
```

**Response**:
```json
{
  "total_vector_count": 150,
  "dimension": 1536,
  "index_fullness": 0.01
}
```

## Usage Examples

### Python Example

```python
import requests

# Query the RAG system
response = requests.post(
    "http://localhost:8000/api/query",
    json={
        "query": "What is the capital of France?",
        "top_k": 3,
        "temperature": 0.7
    }
)

result = response.json()
print(f"Response: {result['response']}")
print(f"Number of sources: {len(result['sources'])}")

# Index new documents
response = requests.post(
    "http://localhost:8000/api/index",
    json={
        "documents": [
            {
                "content": "Paris is the capital and most populous city of France.",
                "metadata": {"source": "geography.txt", "topic": "europe"}
            }
        ]
    }
)

print(f"Indexed: {response.json()['indexed_count']} documents")
```

### JavaScript Example

```javascript
// Query the RAG system
fetch('http://localhost:8000/api/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'What is Python?',
    top_k: 5,
    temperature: 0.7
  })
})
  .then(response => response.json())
  .then(data => {
    console.log('Response:', data.response);
    console.log('Sources:', data.sources);
  });

// Index documents
fetch('http://localhost:8000/api/index', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    documents: [
      {
        content: 'Python is a high-level programming language...',
        metadata: { source: 'python_intro.txt' }
      }
    ]
  })
})
  .then(response => response.json())
  .then(data => console.log('Indexed:', data.indexed_count, 'documents'));
```

## Project Structure

```
rag_demo/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in git)
├── .env.example           # Example environment file
├── .gitignore             # Git ignore rules
├── spec.md                # Project specification
├── design.md              # System design document
├── implementation.md      # Implementation TODO
├── README.md              # This file
├── config/
│   ├── __init__.py
│   └── settings.py        # Application settings
├── services/
│   ├── __init__.py
│   ├── embedding_service.py    # OpenAI embeddings
│   ├── vector_db_service.py    # Pinecone operations
│   └── llm_service.py          # OpenAI LLM operations
├── api/
│   ├── __init__.py
│   ├── models.py          # Pydantic models
│   └── routes.py          # API endpoints
└── utils/
    ├── __init__.py
    └── helpers.py         # Utility functions
```

## Configuration

All configuration is done through environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `PINECONE_API_KEY` | Pinecone API key | Required |
| `PINECONE_ENVIRONMENT` | Pinecone environment | Optional |
| `PINECONE_INDEX_NAME` | Pinecone index name | rag-demo |
| `EMBEDDING_MODEL` | OpenAI embedding model | text-embedding-3-small |
| `LLM_MODEL` | OpenAI LLM model | gpt-4 |
| `LLM_TEMPERATURE` | Response randomness (0-2) | 0.7 |
| `TOP_K_RESULTS` | Number of context docs | 5 |

## Development

### Running Tests

```bash
# Install test dependencies
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

## Troubleshooting

### Issue: "Index not initialized"

**Solution**: Make sure Pinecone API key and environment are correctly set in `.env` file.

### Issue: "OpenAI API error"

**Solution**:
- Check that your OpenAI API key is valid
- Ensure you have sufficient API credits
- Check your API rate limits

### Issue: "Connection timeout"

**Solution**:
- Check your internet connection
- Verify firewall settings
- Try increasing timeout values in service files

### Issue: "No relevant context found"

**Solution**:
- Make sure you've indexed documents using the `/index` endpoint
- Check that documents are relevant to your queries
- Try adjusting the `top_k` parameter

## Performance Tips

1. **Batch Indexing**: Index multiple documents at once for better performance
2. **Caching**: Consider caching frequent queries
3. **Model Selection**: Use `gpt-3.5-turbo` for faster, cheaper responses
4. **Chunk Size**: Adjust `chunk_size` in settings for optimal retrieval

## Security Considerations

- Never commit `.env` file to version control
- Use environment-specific API keys
- Implement rate limiting in production
- Add authentication for production deployments
- Validate and sanitize all user inputs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License

## Support

For issues and questions:
- Check the troubleshooting section
- Review API documentation at `/docs`
- Check application logs for error details

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Vector database by [Pinecone](https://www.pinecone.io/)
- AI models by [OpenAI](https://openai.com/)
