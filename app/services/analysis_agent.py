"""自然語言資料分析 Agent。

包裝 LangChain 的 Pandas DataFrame Agent：使用者用中文提問，
LLM 自動撰寫並執行 pandas 程式碼，最後回傳一段中文結論。

安全性備註：
    Pandas Agent 會在本機 Python 執行環境中執行 LLM 產生的程式碼
    （需 allow_dangerous_code=True）。本專案定位為「本機單人分析工具」，
    上傳的資料不會離開你的電腦。請勿將此服務直接對外網開放，
    也不要載入不信任來源的檔案。
"""

from __future__ import annotations

import os

import pandas as pd
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from app.data_loader import summarize_schema

MODEL_NAME = "gemini-3.1-flash-lite"

_PREFIX = """你是一位嚴謹的資料分析師，正在協助非技術背景的教會/社群同工分析一份 pandas DataFrame（變數名為 `df`）。

請遵守下列規則：
1. 一律使用「繁體中文」回答。
2. 先思考需要哪些欄位與計算，再撰寫 pandas 程式碼求證，不要憑空猜測數字。
3. 最終回覆要包含：直接的結論、關鍵數字（標明欄位與單位），必要時補一句簡短說明。
4. 若問題無法從資料回答，請誠實說明缺少哪些資訊，不要捏造。
5. 日期欄位若為文字，請先用 pd.to_datetime 轉換再做時間相關分析。
"""


def _coerce_text(output: object) -> str:
    """把 Agent 回傳值統一轉成純文字。

    langchain 1.x + Gemini 有時會回傳「內容區塊列表」
    （如 [{"type": "text", "text": "...", "extras": {...}}]），
    直接 str() 會印出整包 dict。這裡只抽出可讀的文字部分。
    """
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        return str(output.get("text") or output.get("output") or "")
    if isinstance(output, (list, tuple)):
        parts: list[str] = []
        for block in output:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type", "text") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(p for p in parts if p)
    return str(output)


def _build_llm() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("未設定 GEMINI_API_KEY，請將 .env.example 複製為 .env 並填入金鑰。")
    return ChatGoogleGenerativeAI(model=MODEL_NAME, google_api_key=api_key, temperature=0)


def _create_agent(llm: ChatGoogleGenerativeAI, df: pd.DataFrame, agent_type: str):
    return create_pandas_dataframe_agent(
        llm,
        df,
        agent_type=agent_type,
        prefix=_PREFIX,
        verbose=True,
        allow_dangerous_code=True,
        include_df_in_prompt=True,
        number_of_head_rows=5,
        max_iterations=8,
        agent_executor_kwargs={"handle_parsing_errors": True},
    )


def run_analysis(df: pd.DataFrame, question: str) -> str:
    """對 DataFrame 執行一次自然語言分析，回傳中文結論字串。

    任何錯誤都會被攔截並轉為友善訊息，不會往外拋出。
    """
    question = (question or "").strip()
    if question == "":
        return "請先輸入想分析的問題。"

    try:
        llm = _build_llm()
    except ValueError as exc:
        return f"⚠️ {exc}"

    # Gemini 的 tool-calling 通常最穩定；若失敗則退回 ReAct 文字模式。
    # 傳入 df 的副本：Pandas Agent 的 REPL 會直接操作同一個物件，
    # 若讓它就地修改（例如新增衍生欄位），會污染呼叫端的 DataFrame。
    for agent_type in ("tool-calling", "zero-shot-react-description"):
        try:
            agent = _create_agent(llm, df.copy(), agent_type)
            result = agent.invoke({"input": question})
            answer = _coerce_text(result.get("output", "")).strip()
            if answer:
                return answer
        except Exception as exc:  # noqa: BLE001 - 對使用者一律回傳可讀訊息
            last_error = exc
            continue

    return (
        "😥 分析時發生問題，請換個問法或確認資料內容。\n\n"
        f"技術細節：{last_error}\n\n"
        f"目前資料結構：\n{summarize_schema(df)}"
    )
