from __future__ import annotations

from rag_system_core.types import ChunkRecord, GenerationClient, QueryResult


class GenerationService:
    def __init__(self, generation_client: GenerationClient, system_prompt: str | None = None) -> None:
        self.generation_client = generation_client
        self.system_prompt = system_prompt or (
            "You are a helpful RAG assistant. Answer only from the retrieved context."
        )
        self.last_prompt = ""

    def build_prompt(self, *, question: str, context_chunks: list[ChunkRecord]) -> str:
        context = "\n\n".join(chunk.content for chunk in context_chunks) if context_chunks else "No context retrieved."
        return (
            "[System Prompt]\n"
            f"{self.system_prompt}\n\n"
            "[Retrieved Context]\n"
            f"{context}\n\n"
            "[User Query]\n"
            f"{question}"
        )

    def call_llm(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.generation_client.generate(prompt)

    def generate(self, *, question: str, context_chunks: list[ChunkRecord]) -> QueryResult:
        prompt = self.build_prompt(question=question, context_chunks=context_chunks)
        answer = self.call_llm(prompt)
        return QueryResult(answer=answer, prompt=prompt, context_chunks=context_chunks)
