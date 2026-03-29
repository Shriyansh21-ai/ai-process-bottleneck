from typing import List
import tiktoken

class TextChunker:
    def __init__(self, chunk_size=400, overlap=80):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def chunk_text(self, text: str) -> List[str]:
        tokens = self.encoder.encode(text)
        chunks = []

        start = 0
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoder.decode(chunk_tokens)
            chunks.append(chunk_text)
            start += self.chunk_size - self.overlap

        return chunks
