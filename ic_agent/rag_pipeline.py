"""Local RAG indexing and retrieval for IC Agent.

This module builds a ChromaDB index from local knowledge documents and provides
an API to retrieve grounded context for analyzer/agent prompts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ic_agent.config import CHROMA_PERSIST_DIR, KNOWLEDGE_DIR


logger = logging.getLogger(__name__)

_COLLECTION_NAME = "ic_knowledge"


def _build_embeddings() -> HuggingFaceEmbeddings:
    """Create local sentence-transformer embeddings."""
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _load_knowledge_documents(knowledge_dir: str) -> list[Any]:
    """Load local IC/OPPM policy documents from the knowledge folder."""
    path = Path(knowledge_dir)
    path.mkdir(parents=True, exist_ok=True)

    docs: list[Any] = []
    patterns = ["**/*.md", "**/*.txt", "**/*.json", "**/*.csv"]
    for pattern in patterns:
        loader = DirectoryLoader(
            str(path),
            glob=pattern,
            show_progress=False,
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        docs.extend(loader.load())
    return docs


def build_knowledge_index(
    knowledge_dir: str = KNOWLEDGE_DIR,
    persist_directory: str = CHROMA_PERSIST_DIR,
) -> dict[str, int]:
    """Build and persist ChromaDB index from local knowledge files.

    Chunking target is approximately 300 tokens with 50-token overlap.
    We use character lengths as a practical approximation for token counts.
    """
    docs = _load_knowledge_documents(knowledge_dir)
    if not docs:
        logger.warning("No knowledge documents found in %s", knowledge_dir)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=_build_embeddings(),
        persist_directory=persist_directory,
        collection_name=_COLLECTION_NAME,
    )
    vectorstore.persist()

    stats = {
        "documents_loaded": len(docs),
        "chunks_indexed": len(chunks),
    }
    logger.info("Built Chroma index: %s", stats)
    return stats


def _get_vectorstore(persist_directory: str = CHROMA_PERSIST_DIR) -> Chroma:
    """Open an existing Chroma vector store."""
    return Chroma(
        collection_name=_COLLECTION_NAME,
        persist_directory=persist_directory,
        embedding_function=_build_embeddings(),
    )


def query_knowledge(question: str, top_k: int = 5) -> str:
    """Retrieve top-k grounded context chunks for a query."""
    query = (question or "").strip()
    if not query:
        return ""

    try:
        vectorstore = _get_vectorstore()
        retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
        docs = retriever.get_relevant_documents(query)
    except Exception as exc:
        logger.warning("Knowledge query failed, returning empty context: %s", exc)
        return ""

    if not docs:
        return ""

    lines: list[str] = []
    for idx, doc in enumerate(docs, start=1):
        source = str(doc.metadata.get("source", "local_knowledge"))
        content = str(doc.page_content or "").strip()
        if not content:
            continue
        lines.append(f"[Chunk {idx} | Source: {Path(source).name}]\n{content}")

    return "\n\n".join(lines)


def main() -> None:
    """CLI entrypoint for building the local knowledge index."""
    stats = build_knowledge_index()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
