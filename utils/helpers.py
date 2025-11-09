from typing import List, Dict, Any
import uuid


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: The text to chunk
        chunk_size: Maximum size of each chunk in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if not text or chunk_size <= 0:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        # Calculate end position
        end = start + chunk_size

        # If not the last chunk, try to break at a sentence or word boundary
        if end < len(text):
            # Look for sentence boundaries (. ! ?)
            sentence_end = max(
                text.rfind('. ', start, end),
                text.rfind('! ', start, end),
                text.rfind('? ', start, end)
            )

            if sentence_end > start:
                end = sentence_end + 1
            else:
                # Look for word boundary (space)
                space_pos = text.rfind(' ', start, end)
                if space_pos > start:
                    end = space_pos

        # Extract chunk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position, accounting for overlap
        start = end - overlap if end < len(text) else len(text)

    return chunks


def format_context(sources: List[Dict[str, Any]]) -> List[str]:
    """
    Format source documents into context strings.

    Args:
        sources: List of source dictionaries with 'content' key

    Returns:
        List of formatted context strings
    """
    context = []
    for source in sources:
        content = source.get("content", "").strip()
        if content:
            context.append(content)

    return context


def generate_document_id(prefix: str = "doc") -> str:
    """
    Generate a unique document ID.

    Args:
        prefix: Prefix for the document ID

    Returns:
        Unique document ID string
    """
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def prepare_documents_for_indexing(
    contents: List[str],
    metadatas: List[Dict[str, Any]] = None,
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Prepare documents for indexing by chunking and adding metadata.

    Args:
        contents: List of document contents
        metadatas: List of metadata dictionaries (one per document)
        chunk_size: Size of each chunk in characters
        overlap: Overlap between chunks in characters

    Returns:
        List of prepared documents with id, content, and metadata
    """
    if metadatas is None:
        metadatas = [{} for _ in contents]

    if len(contents) != len(metadatas):
        raise ValueError("Number of contents and metadatas must match")

    prepared_docs = []

    for doc_idx, (content, metadata) in enumerate(zip(contents, metadatas)):
        # Chunk the content
        chunks = chunk_text(content, chunk_size, overlap)

        for chunk_idx, chunk in enumerate(chunks):
            # Create metadata for this chunk
            chunk_metadata = metadata.copy()
            chunk_metadata["content"] = chunk
            chunk_metadata["document_index"] = doc_idx
            chunk_metadata["chunk_index"] = chunk_idx
            chunk_metadata["total_chunks"] = len(chunks)

            # Generate unique ID
            doc_id = generate_document_id()

            prepared_docs.append({
                "id": doc_id,
                "content": chunk,
                "metadata": chunk_metadata
            })

    return prepared_docs


def validate_embedding_dimension(embedding: List[float], expected_dim: int = 1024) -> bool:
    """
    Validate that an embedding has the expected dimension.

    Args:
        embedding: The embedding vector
        expected_dim: Expected dimension size

    Returns:
        True if dimension matches, False otherwise
    """
    return len(embedding) == expected_dim


def truncate_text(text: str, max_length: int = 500) -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - 3] + "..."
