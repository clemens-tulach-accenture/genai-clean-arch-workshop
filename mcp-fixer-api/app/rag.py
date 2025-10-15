import os, re
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer
import faiss

class KnowledgeBase:
    def __init__(self, kb_dir: str):
        self.kb_dir = kb_dir
        self._chunks: List[str] = []
        self._model = None
        self._index = None
        self._load()

    def _load_files(self) -> str:
        files = sorted([f for f in os.listdir(self.kb_dir) if f.endswith(".md")])
        corpus = ""
        for f in files:
            path = os.path.join(self.kb_dir, f)
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            corpus += f"\n\n# Source: {f}\n\n{content}"
        return corpus

    def _load(self):
        corpus = self._load_files()
        self._chunks = re.split(r'\n\s*\n', corpus.strip())
        self._model = SentenceTransformer('all-MiniLM-L6-v2')
        emb = self._model.encode(self._chunks)
        dim = emb.shape[1]
        self._index = faiss.IndexFlatL2(dim)
        self._index.add(np.array(emb))

    def retrieve(self, query: str, top_k: int = 5) -> str:
        qemb = self._model.encode([query])
        _, idx = self._index.search(np.array(qemb), top_k)
        result = "\n\n".join([self._chunks[i] for i in idx[0]])
        return result.replace('\u200b', '').replace('\ufeff', '')

_kb_cache = {}
def get_kb(kb_dir: str) -> KnowledgeBase:
    if kb_dir not in _kb_cache:
        _kb_cache[kb_dir] = KnowledgeBase(kb_dir)
    return _kb_cache[kb_dir]
