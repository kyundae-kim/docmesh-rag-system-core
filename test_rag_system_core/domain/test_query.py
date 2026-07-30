from __future__ import annotations

from pathlib import Path

from test_rag_system_core.support import authenticated_user, create_test_rig

USER_A = authenticated_user("user-a")
USER_B = authenticated_user("user-b")


def test_query_filters_results_by_authenticated_user(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    rig.core.ingest_text(user=USER_A, text="alpha document only for user a", source="a.txt")
    rig.core.ingest_text(user=USER_B, text="beta document only for user b", source="b.txt")

    response = rig.core.query(user=USER_A, question="Where is alpha?", top_k=3)

    assert response.answer.startswith("ANSWER::Where is alpha?::")
    assert "alpha document only for user a" in response.answer
    assert all(chunk.user_id == "user-a" for chunk in response.context_chunks)
    assert all("user b" not in chunk.content for chunk in response.context_chunks)


def test_query_prompt_includes_system_query_and_context(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    rig.core.ingest_text(user=USER_A, text="alpha context block", source="a.txt")

    response = rig.core.query(user=USER_A, question="Summarize alpha", top_k=1)

    prompt = rig.generation_client.last_prompt
    assert response.answer.startswith("ANSWER::Summarize alpha::")
    assert "[System Prompt]" in prompt
    assert "[Retrieved Context]" in prompt
    assert "alpha context block" in prompt
    assert "[User Query]\nSummarize alpha" in prompt
