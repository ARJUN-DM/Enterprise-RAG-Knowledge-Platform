"""Golden QA dataset loader.

Loads and validates the golden QA dataset from a JSONL file.
Each line contains: question, answer, relevant_chunk_ids[], role.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

from structlog import get_logger

logger = get_logger(__name__)


class GoldenQAItem(NamedTuple):
    """A single entry in the golden QA dataset."""

    question: str
    expected_answer: str
    relevant_chunk_ids: list[str]
    role: str


def load_golden_qa(path: str | Path = "evals/golden_qa.jsonl") -> list[GoldenQAItem]:
    """Load and validate the golden QA dataset from a JSONL file.

    Returns a list of GoldenQAItem tuples. Returns an empty list if the
    file doesn't exist or is empty (the eval runner will skip recall checks).
    """
    path = Path(path)
    if not path.exists():
        logger.warning("golden_qa_not_found", path=str(path))
        return []

    items: list[GoldenQAItem] = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                item = GoldenQAItem(
                    question=data["question"],
                    expected_answer=data.get("expected_answer", ""),
                    relevant_chunk_ids=data.get("relevant_chunk_ids", []),
                    role=data.get("role", "admin"),
                )
                items.append(item)
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning(
                    "golden_qa_parse_error", line=line_num, error=str(exc)
                )

    logger.info("golden_qa_loaded", count=len(items))
    return items
