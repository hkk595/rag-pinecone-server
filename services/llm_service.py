import time
from typing import List, Dict, Any
from openai import OpenAI
from config.settings import settings


class LLMService:
    """Service for generating responses using OpenAI LLM."""

    def __init__(self):
        """Initialize the OpenAI client."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    def generate_response(
        self,
        query: str,
        context: List[str],
        temperature: float = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> str:
        """
        Generate a response using the LLM with provided context.

        Args:
            query: The user's question
            context: List of relevant context strings from vector search
            temperature: Sampling temperature (uses settings default if None)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            Generated response string

        Raises:
            Exception: If all retry attempts fail
        """
        if temperature is None:
            temperature = settings.llm_temperature

        max_tokens = settings.max_response_tokens

        # GPT-5 doesn't support a configurable temperature parameter, unlike older models
        if "gpt-5" in self.model:
            temperature = 1
            max_tokens = None  # remove upper bound for visible output tokens and reasoning tokens in GPT-5 model

        # Construct the prompt with context
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(query, context)

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "developer", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_completion_tokens=max_tokens
                )

                return response.choices[0].message.content

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"LLM API error (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to generate response after {max_retries} attempts: {e}")

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for the LLM.

        Returns:
            System prompt string
        """
        return """You are a helpful AI assistant that answers questions based on the provided context.

Your responsibilities:
1. Answer questions accurately using the context provided
2. If the context doesn't contain enough information to answer the question, say so clearly
3. Be concise and direct in your responses
4. Cite specific parts of the context when relevant
5. If the question is unclear, ask for clarification

Important guidelines:
- Only use information from the provided context
- Do not make up or infer information not present in the context
- If multiple pieces of context conflict, acknowledge the discrepancy
- Be honest about limitations in the available information"""

    def _create_user_prompt(self, query: str, context: List[str]) -> str:
        """
        Create the user prompt with context and query.

        Args:
            query: The user's question
            context: List of context strings

        Returns:
            Formatted user prompt
        """
        if not context:
            return f"""Question: {query}

Context: No relevant context found.

Please answer the question or indicate that you don't have enough information to provide a meaningful answer."""

        # Format context with numbering
        formatted_context = "\n\n".join([
            f"Context {i+1}:\n{ctx}"
            for i, ctx in enumerate(context)
        ])

        return f"""Context Information:
{formatted_context}

Question: {query}

Please answer the question based on the context provided above. If the context doesn't contain relevant information, please indicate that."""

    def generate_response_with_metadata(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        temperature: float = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> str:
        """
        Generate a response using sources with metadata.

        Args:
            query: The user's question
            sources: List of source dictionaries with 'content' and 'metadata'
            temperature: Sampling temperature (uses settings default if None)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries

        Returns:
            Generated response string

        Raises:
            Exception: If all retry attempts fail
        """
        # Extract just the content for context
        context = [source.get("content", "") for source in sources if source.get("content")]

        return self.generate_response(
            query=query,
            context=context,
            temperature=temperature,
            max_retries=max_retries,
            retry_delay=retry_delay
        )
