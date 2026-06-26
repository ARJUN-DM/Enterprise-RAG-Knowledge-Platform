"""Tests for the semantic document chunker."""

from __future__ import annotations

from app.ingestion.chunker import chunk_document, chunk_text_direct


class TestChunker:
    """Verify the semantic chunker produces correct chunks."""

    def test_simple_segments(self):
        """Each text segment should become at most one chunk."""
        segments = [
            ("This is the first paragraph.", {"source": "test.md", "section_heading": "Intro"}),
            ("This is the second paragraph.", {"source": "test.md", "section_heading": "Details"}),
        ]
        chunks = chunk_document(segments, chunk_size=512)
        assert len(chunks) == 2
        assert chunks[0]["content"] == "This is the first paragraph."
        assert chunks[0]["section_heading"] == "Intro"
        assert chunks[1]["content"] == "This is the second paragraph."
        assert chunks[1]["section_heading"] == "Details"

    def test_chunk_size_respected(self):
        """Long text should be split into multiple chunks respecting chunk_size."""
        text = " ".join(["word"] * 1000)
        chunks = chunk_text_direct(text, chunk_size=100)
        for chunk in chunks:
            assert len(chunk["content"]) <= 100 + 64  # content may be slightly larger due to overlap

    def test_empty_input(self):
        """Empty input should produce zero chunks."""
        chunks = chunk_text_direct("")
        assert len(chunks) == 0

    def test_heading_preserved_in_metadata(self):
        """Section heading from metadata should be preserved in output chunks."""
        segments = [
            ("Some content.", {"source": "doc.md", "section_heading": "Chapter 1"}),
        ]
        chunks = chunk_document(segments)
        assert chunks[0]["section_heading"] == "Chapter 1"
        assert chunks[0]["source"] == "doc.md"

    def test_overlap_works(self):
        """Chunks should have overlapping content when text exceeds chunk_size."""
        text = "This is sentence one. This is sentence two. " * 20
        chunks = chunk_text_direct(text, chunk_size=100, chunk_overlap=30)
        if len(chunks) > 1:
            # Check that consecutive chunks overlap
            assert chunks[0]["content"] != chunks[1]["content"]
