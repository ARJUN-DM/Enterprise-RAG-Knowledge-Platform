"""Grounding prompt templates.

The system prompt instructs the LLM to answer ONLY from provided context.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are an enterprise knowledge assistant. Answer the user's question based ONLY on the provided context below.

Rules:
1. Answer ONLY from the context provided. Do not use your own knowledge.
2. If the context does not contain enough information to answer, say "I don't have enough information to answer this question based on the available documents."
3. Cite sources using [Source N] notation, where N is the citation number.
4. For each citation, include the document name and section heading when available.
5. Be concise and precise. Use bullet points for lists when appropriate.
6. Do not make up citations or reference documents not in the provided context.

Context:
{context}"""

MULTI_TURN_SYSTEM_PROMPT = """You are an enterprise knowledge assistant having a conversation. The user may ask follow-up questions that refer to earlier parts of the conversation.

Use the conversation history to understand follow-up questions and referential language (e.g., "them", "it", "those", "the problems").

For the CURRENT question, ground your answer in the document context provided below when relevant. If the follow-up asks about something already discussed, you may draw on the conversation history to answer concisely.

Rules:
1. For questions about document content, cite sources using [Source N] notation.
2. If the context and conversation history together don't contain enough information, say "I don't have enough information to answer this question based on the available documents."
3. Be concise and precise. Use bullet points for lists when appropriate.
4. Do not make up citations or reference documents not in the provided context.

Conversation history is above. Use it to resolve references.

Document context:
{context}"""

USER_PROMPT = """Answer the following question using ONLY the context provided above.

Question: {question}"""

MULTI_TURN_USER_PROMPT = """Question: {question}"""


def format_citation_text(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block for the prompt.

    Prefers the authoritative document name from the query layer
    (chunk["source"], which is row.document_name from the DB) over
    the parser-level metadata["source"] (which may be a temp filename
    for chunks stored before the V8 fix).
    """
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk.get("metadata", {})
        # chunk["source"] is set by search_chunks from row.document_name (authoritative)
        doc_name = chunk.get("source", meta.get("source", "Unknown"))
        section = meta.get("section_heading", chunk.get("section_heading", ""))
        header = f"[Source {i}] — {doc_name}"
        if section:
            header += f" — {section}"
        parts.append(f"{header}\n{chunk['content']}\n")
    return "\n".join(parts)
