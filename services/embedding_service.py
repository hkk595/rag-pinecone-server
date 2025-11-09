import time
from typing import List
from openai import OpenAI
from config.settings import settings


class EmbeddingService:
    """Service for generating text embeddings using OpenAI API."""

    def __init__(self):
        """Initialize the OpenAI client."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension

    def generate_embedding(
        self,
        text: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> List[float]:
        """
        Generate embedding for a given text.

        Args:
            text: The text to generate embedding for
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If all retry attempts fail
        """
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text,
                    dimensions=self.dimension
                )
                return response.data[0].embedding

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"Embedding API error (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to generate embedding after {max_retries} attempts: {e}")

    def generate_embeddings_batch(
        self,
        texts: List[str],
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to generate embeddings for
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            List of embedding vectors

        Raises:
            Exception: If all retry attempts fail
        """
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                    dimensions=self.dimension
                )
                return [data.embedding for data in response.data]

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"Batch embedding API error (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to generate embeddings after {max_retries} attempts: {e}")
