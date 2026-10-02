"""Offline embeddings for workshops without API access.

"Hashing trick": each word (and word pair) is hashed into one of N buckets and
the vector is L2-normalised. It captures keyword overlap, not meaning, so
"wheelchair" will not match "mobility aid" unless both words appear. That
limitation is a good discussion point in the RAG exercise: switch
EMBEDDING_MODEL to a real model and compare the retrieved chunks.
"""

from __future__ import annotations

import hashlib
import math
import re

from langchain_core.embeddings import Embeddings

_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "are", "be", "on", "with", "by", "at", "it", "as", "i", "my", "me", "can", "do", "what", "how", "who", "get", "you", "your", "i'm", "am", "if", "there", "any", "much", "does"}


def _words(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9$]+", text.lower()):
        if w in _STOP:
            continue
        for suf in ("ies", "ing", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


class HashEmbeddings(Embeddings):
    def __init__(self, dim: int = 4096):
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        words = _words(text)
        feats = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
        counts: dict[int, float] = {}
        for f in feats:
            h = int(hashlib.md5(f.encode()).hexdigest(), 16) % self.dim
            counts[h] = counts.get(h, 0.0) + (1.0 if "_" not in f else 0.5)
        for h, c in counts.items():
            vec[h] = 1.0 + math.log(c)  # sub-linear term frequency
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
