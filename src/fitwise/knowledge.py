"""Knowledge retrieval.

Character n-gram TF-IDF, not embeddings: the corpus is 18 short Chinese entries,
where a local model would add a dependency, a download, and a new failure mode
without improving recall. Every hit keeps its source so answers can cite.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

DEFAULT_KB = Path(__file__).parent / "data" / "kb.jsonl"


@dataclass
class Hit:
    id: str
    title: str
    content: str
    topic: str
    source: str
    score: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "topic": self.topic,
            "source": self.source,
            "score": round(self.score, 4),
        }


class KnowledgeBase:
    def __init__(self, path: str | Path = DEFAULT_KB) -> None:
        path = Path(path)
        self.entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not self.entries:
            raise ValueError(f"empty knowledge base: {path}")
        self._texts = [f"{e['title']} {e['content']} {e['topic']}" for e in self.entries]
        # char_wb 2-3 grams handle Chinese without a tokenizer dependency.
        self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3), min_df=1)
        self._matrix = self._vec.fit_transform(self._texts)

    def search(self, query: str, k: int = 3) -> list[Hit]:
        if not query.strip():
            return []
        q = self._vec.transform([query])
        scores = linear_kernel(q, self._matrix).ravel()
        order = scores.argsort()[::-1][:k]
        hits = []
        for idx in order:
            if scores[idx] <= 0:
                continue
            e = self.entries[idx]
            hits.append(
                Hit(
                    id=e["id"],
                    title=e["title"],
                    content=e["content"],
                    topic=e["topic"],
                    source=e["source"],
                    score=float(scores[idx]),
                )
            )
        return hits

    def get(self, entry_id: str) -> Hit | None:
        for e in self.entries:
            if e["id"] == entry_id:
                return Hit(e["id"], e["title"], e["content"], e["topic"], e["source"], 1.0)
        return None

    def __len__(self) -> int:
        return len(self.entries)
