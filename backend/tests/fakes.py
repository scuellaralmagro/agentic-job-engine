"""Deterministic test doubles. Nothing here touches the network."""
import math

# A tiny fixed vocabulary. Vectors are L2-normalised bag-of-words, so cosine
# similarity behaves like real embeddings do for overlapping topics — an offer
# about nursing scores ~0 against a backend profile, which is exactly the
# behaviour the prefilter gate depends on.
VOCAB = [
    "python",
    "backend",
    "fastapi",
    "postgres",
    "kubernetes",
    "java",
    "frontend",
    "react",
    "nurse",
    "sales",
    "madrid",
    "engineer",
]


def bag_of_words_vector(text: str) -> list[float]:
    lowered = text.lower()
    values = [1.0 if word in lowered else 0.0 for word in VOCAB]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


class FakeEmbeddings:
    def __init__(self) -> None:
        self.documents_calls = 0
        self.embedded_texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.documents_calls += 1
        self.embedded_texts.extend(texts)
        return [bag_of_words_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return bag_of_words_vector(text)
