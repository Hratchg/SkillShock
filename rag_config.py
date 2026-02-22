"""
SkillShock RAG Config — RapidFire LangChainRagSpec setup

Builds a semantic retrieval pipeline using RapidFire's LangChainRagSpec
with HuggingFace embeddings and FAISS vector store over SkillShock career data.
"""

from __future__ import annotations

from typing import Any

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rapidfireai.evals.rag.rag_pipeline import LangChainRagSpec

from career_loader import CareerDataLoader

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def build_rag_spec(data: dict[str, Any], k: int = 8) -> LangChainRagSpec:
    """Create and initialize a LangChainRagSpec for SkillShock career data.

    Args:
        data: Parsed output.json dictionary.
        k: Number of documents to retrieve per query.

    Returns:
        A ready-to-query LangChainRagSpec with built FAISS index.
    """
    spec = LangChainRagSpec(
        document_loader=CareerDataLoader(data),
        text_splitter=RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " "],
        ),
        embedding_cls=HuggingFaceEmbeddings,
        embedding_kwargs={
            "model_name": EMBEDDING_MODEL,
            "model_kwargs": {"device": "cpu"},
        },
        search_type="similarity",
        search_kwargs={"k": k},
        enable_gpu_search=False,
    )
    spec.build_index()
    return spec


def retrieve_context(spec: LangChainRagSpec, profile: dict[str, Any]) -> str:
    """Build a semantic query from a student profile and retrieve career data.

    Args:
        spec: Initialized LangChainRagSpec.
        profile: Dict with keys like major, current_role, target_role, etc.

    Returns:
        Formatted string of relevant career data passages.
    """
    parts: list[str] = []
    if profile.get("major"):
        parts.append(f"{profile['major']} graduate")
    if profile.get("current_role"):
        parts.append(f"currently {profile['current_role']}")
    if profile.get("current_industry"):
        parts.append(f"in {profile['current_industry']}")
    if profile.get("target_role"):
        parts.append(f"targeting {profile['target_role']}")
    query = ", ".join(parts) or "career planning advice"
    results = spec.get_context([query], use_reranker=False)
    return results[0] if results else "No relevant data found."
