from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str = Field(..., description="The user's question", min_length=1)
    top_k: Optional[int] = Field(5, description="Number of context documents to retrieve", ge=1, le=20)
    temperature: Optional[float] = Field(0.7, description="LLM temperature for response generation", ge=0.0, le=2.0)

    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or only whitespace')
        return v.strip()


class Source(BaseModel):
    """Model for a source document."""
    content: str = Field(..., description="The content of the source document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the source")
    score: float = Field(..., description="Similarity score", ge=0.0, le=1.0)


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    response: str = Field(..., description="The generated response")
    sources: List[Source] = Field(default_factory=list, description="Source documents used for the response")


class DocumentInput(BaseModel):
    """Model for a single document to be indexed."""
    content: str = Field(..., description="The document content", min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata for the document")

    @validator('content')
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Document content cannot be empty or only whitespace')
        return v.strip()


class IndexRequest(BaseModel):
    """Request model for indexing documents."""
    documents: List[DocumentInput] = Field(..., description="List of documents to index", min_items=1)


class IndexResponse(BaseModel):
    """Response model for indexing endpoint."""
    indexed_count: int = Field(..., description="Number of documents successfully indexed", ge=0)
    status: str = Field(..., description="Status of the indexing operation")


class ServiceStatus(BaseModel):
    """Model for individual service status."""
    status: str = Field(..., description="Service status")
    message: Optional[str] = Field(None, description="Additional status message")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(..., description="Overall health status")
    services: Dict[str, ServiceStatus] = Field(default_factory=dict, description="Status of individual services")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
