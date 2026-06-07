from __future__ import annotations

from pathlib import Path

from test_rag_system_core.support import create_test_rig


def test_query_filters_results_by_token_derived_user_id(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    rig.core.ingest_text(token="token-a", text="alpha document only for token a", source="a.txt")
    rig.core.ingest_text(token="token-b", text="beta document only for token b", source="b.txt")

    response = rig.core.query(token="token-a", question="Where is alpha?", top_k=3)

    assert response.answer.startswith("ANSWER::Where is alpha?::")
    assert "alpha document only for token a" in response.answer
    assert all(chunk.user_id == "token-a" for chunk in response.context_chunks)
    assert all("token b" not in chunk.content for chunk in response.context_chunks)


def test_query_prompt_includes_system_query_and_context(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    rig.core.ingest_text(token="token-a", text="alpha context block", source="a.txt")

    response = rig.core.query(token="token-a", question="Summarize alpha", top_k=1)

    prompt = rig.generation_client.last_prompt
    assert response.answer.startswith("ANSWER::Summarize alpha::")
    assert "[System Prompt]" in prompt
    assert "[Retrieved Context]" in prompt
    assert "alpha context block" in prompt
    assert "[User Query]\nSummarize alpha" in prompt
