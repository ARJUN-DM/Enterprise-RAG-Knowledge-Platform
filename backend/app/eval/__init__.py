"""RAG Evaluation Framework.

Metrics:
    - Faithfulness: LLM-judged claim grounding
    - Answer Relevance: cosine similarity between query and answer embeddings
    - Context Precision: fraction of retrieved chunks actually used in the answer
    - Context Recall: comparison against golden QA dataset
"""

from __future__ import annotations
