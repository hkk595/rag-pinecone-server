from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str
    embedding_model: str = "text-embedding-3-large"
    embedding_dimension: int = 1024

    llm_model: str = "gpt-5"
    llm_temperature: float = 0.7

    # Pinecone Configuration
    pinecone_api_key: str
    pinecone_environment: Optional[str] = None
    pinecone_index_host: str = "https://rag-app.pinecone.io"
    pinecone_index_name: str = "rag-app"
    pinecone_namespace: str = "__default__"

    # RAG Configuration
    top_k_results: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_response_tokens: int = 1000

    # API Configuration
    api_title: str = "RAG Application API"
    api_version: str = "1.0.0"
    api_description: str = "A Retrieval-Augmented Generation API using Pinecone and OpenAI"

    # Server Configuration
    service_address: str = "http://127.0.0.1"
    service_port: int = 8000
    service_url: str = f"{service_address}:{service_port}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Singleton instance
settings = Settings()
