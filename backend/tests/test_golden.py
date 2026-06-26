"""Tests for the golden QA dataset loader."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.eval.golden import GoldenQAItem, load_golden_qa


class TestGoldenQALoader:
    """Verify the golden QA dataset loader works correctly."""

    def test_load_valid_file(self):
        """Should parse valid JSONL into GoldenQAItem objects."""
        lines = [
            {"question": "Q1", "expected_answer": "A1", "relevant_chunk_ids": ["c1"], "role": "hr"},
            {"question": "Q2", "expected_answer": "A2", "relevant_chunk_ids": ["c2", "c3"], "role": "engineering"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for line in lines:
                f.write(json.dumps(line) + "\n")
            tmp_path = f.name

        try:
            items = load_golden_qa(tmp_path)
            assert len(items) == 2
            assert isinstance(items[0], GoldenQAItem)
            assert items[0].question == "Q1"
            assert items[0].role == "hr"
            assert items[1].relevant_chunk_ids == ["c2", "c3"]
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_file_not_found(self):
        """Should return empty list when file doesn't exist."""
        items = load_golden_qa("/nonexistent/path.jsonl")
        assert items == []

    def test_skip_invalid_lines(self):
        """Should skip malformed JSON lines without crashing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"question": "Valid"}\n')
            f.write("not valid json\n")
            f.write('{"question": "Also valid"}\n')
            tmp_path = f.name

        try:
            items = load_golden_qa(tmp_path)
            assert len(items) == 2
        finally:
            Path(tmp_path).unlink(missing_ok=True)
