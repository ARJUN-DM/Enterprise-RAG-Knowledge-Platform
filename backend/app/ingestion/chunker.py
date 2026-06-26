"""Semantic chunker that splits documents at heading/paragraph boundaries.

Primary strategy: merge consecutive small segments (same section_heading/source)
into larger chunks up to chunk_size, so stored chunks carry meaningful context
instead of single-line fragments.
Fallback: fixed-size chunks with overlap for very long paragraphs.
Never splits a sentence mid-thought.
"""

from __future__ import annotations

import re

# Minimum target size for a merged chunk. The chunker accumulates adjacent
# short segments until at least this many characters is reached, then emits.
_MIN_CHUNK_TARGET = 200


def chunk_document(
    segments: list[tuple[str, dict]],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[dict]:
    """Chunk parsed document segments into embedding-ready pieces.

    Each segment from the parser is a (text, metadata) pair.
    Consecutive small segments that share the same section_heading/source are
    merged into larger chunks (up to chunk_size), so each stored chunk carries
    meaningful context instead of single-line fragments.
    Segments larger than chunk_size are split at sentence boundaries with overlap.
    Does NOT merge across different documents/sources.

    Returns a list of chunk dicts with keys:
        content, metadata, section_heading, source
    """
    chunks: list[dict] = []

    # Accumulator for merging consecutive small segments
    merge_buffer: list[str] = []
    merge_meta: dict | None = None
    merge_heading: str = ""
    merge_source: str = ""
    merge_len: int = 0

    def flush_buffer() -> None:
        """Emit the current merge buffer as a single chunk."""
        nonlocal merge_buffer, merge_meta, merge_heading, merge_source, merge_len
        if not merge_buffer:
            return
        text = "\n\n".join(merge_buffer)
        # Use the metadata from the last segment (source/heading are consistent)
        meta = merge_meta or {}
        chunks.append(
            {
                "content": text,
                "metadata": meta,
                "section_heading": merge_heading,
                "source": merge_source,
            }
        )
        merge_buffer = []
        merge_meta = None
        merge_heading = ""
        merge_source = ""
        merge_len = 0

    for text, metadata in segments:
        seg_heading = metadata.get("section_heading", "")
        seg_source = metadata.get("source", "")

        # Long segment — flush buffer, then split at sentence boundaries
        if len(text) > chunk_size:
            flush_buffer()
            _split_long_segment(text, metadata, chunks, chunk_size, chunk_overlap)
            continue

        # Check if this segment is mergeable with the current buffer:
        #   same heading, same source, and adding it won't exceed chunk_size
        can_merge = (
            merge_buffer
            and seg_heading == merge_heading
            and seg_source == merge_source
            and merge_len + len(text) + 2 <= chunk_size  # +2 for "\n\n" separator
        )

        if can_merge:
            merge_buffer.append(text)
            merge_len += len(text) + 2  # account for separator
        else:
            # If the buffer has content and we can't merge, flush it
            # (but only if it meets the minimum target size)
            if merge_buffer and merge_len >= _MIN_CHUNK_TARGET:
                flush_buffer()
            elif merge_buffer:
                # Buffer is below minimum target but we can't merge — flush anyway
                # to avoid unbounded accumulation
                flush_buffer()

            # Start a new buffer
            merge_buffer = [text]
            merge_meta = metadata
            merge_heading = seg_heading
            merge_source = seg_source
            merge_len = len(text)

    # Flush any remaining buffer content
    if merge_buffer:
        flush_buffer()

    return chunks


def _split_long_segment(
    text: str,
    metadata: dict,
    chunks: list[dict],
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """Split a single long segment at sentence boundaries with overlap."""
    sentences = _split_sentences(text)
    current_chunk: list[str] = []
    current_len = 0

    for sentence in sentences:
        sent_len = len(sentence)
        if current_len + sent_len > chunk_size and current_chunk:
            chunks.append(
                {
                    "content": " ".join(current_chunk),
                    "metadata": metadata,
                    "section_heading": metadata.get("section_heading", ""),
                    "source": metadata.get("source", ""),
                }
            )
            # Keep overlap sentences
            overlap_count = 0
            overlap_len = 0
            overlap_sentences: list[str] = []
            for s in reversed(current_chunk):
                s_len = len(s)
                if overlap_len + s_len > chunk_overlap and overlap_sentences:
                    break
                overlap_sentences.insert(0, s)
                overlap_len += s_len
                overlap_count += 1
            current_chunk = overlap_sentences
            current_len = overlap_len

        current_chunk.append(sentence)
        current_len += sent_len

    if current_chunk:
        chunks.append(
            {
                "content": " ".join(current_chunk),
                "metadata": metadata,
                "section_heading": metadata.get("section_heading", ""),
                "source": metadata.get("source", ""),
            }
        )


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, keeping the delimiter attached."""
    # Simple sentence splitting — handles common patterns
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def chunk_text_direct(
    text: str,
    source: str = "",
    section_heading: str = "",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[dict]:
    """Chunk raw text directly (bypassing the parser)."""
    segments = [(text, {"source": source, "section_heading": section_heading})]
    return chunk_document(segments, chunk_size, chunk_overlap)
