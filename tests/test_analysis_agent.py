"""analysis_agent 純函式測試（不呼叫 LLM）。"""

from app.services.analysis_agent import _coerce_text


def test_coerce_plain_string():
    assert _coerce_text("以斯帖小組") == "以斯帖小組"


def test_coerce_content_block_list():
    # langchain 1.x + Gemini 有時回傳內容區塊列表
    blocks = [
        {"type": "text", "text": "第一段", "extras": {"signature": "xxx"}},
        {"type": "text", "text": "第二段"},
    ]
    assert _coerce_text(blocks) == "第一段\n第二段"


def test_coerce_ignores_non_text_blocks():
    blocks = [
        {"type": "reasoning", "text": "略過我"},
        {"type": "text", "text": "留下我"},
    ]
    assert _coerce_text(blocks) == "留下我"


def test_coerce_dict_with_text_key():
    assert _coerce_text({"text": "答案"}) == "答案"
