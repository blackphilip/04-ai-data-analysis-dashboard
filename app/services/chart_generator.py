"""圖表生成服務。

流程分兩步：
1. suggest_chart_spec：呼叫 Gemini，依使用者問題與資料結構回傳結構化的 ChartSpec。
2. build_figure：純函式，依 ChartSpec 用固定邏輯以 Plotly 繪圖（不執行 LLM 產生的程式碼）。

build_figure 不碰網路，可獨立單元測試。
"""

from __future__ import annotations

import os
import warnings

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from langchain_google_genai import ChatGoogleGenerativeAI

from app.data_loader import summarize_schema
from app.schemas import ChartSpec

MODEL_NAME = "gemini-3.1-flash-lite"

_SYSTEM_PROMPT = """你是資料視覺化專家。請依使用者的問題與下方資料結構，決定最適合的一張圖表規格。

規則：
- x、y、color 只能使用資料中「實際存在」的欄位名稱。
- 想比較不同類別的數量或總和 → bar；觀察隨時間變化的趨勢 → line；
  看組成佔比 → pie；看兩數值關係 → scatter；看單一數值分布 → histogram。
- 若同一個 x 有多列資料，請設定合適的 aggregation（sum / mean / count）。
- 若問題牽涉「各月 / 各年 / 每日」的時間趨勢，x 填該日期欄位，並設定 time_bucket。
- title 用繁體中文。

資料結構：
{schema}
"""


def suggest_chart_spec(df: pd.DataFrame, question: str) -> ChartSpec:
    """呼叫 Gemini 產生 ChartSpec。"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("未設定 GEMINI_API_KEY，請將 .env.example 複製為 .env 並填入金鑰。")

    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, google_api_key=api_key, temperature=0)
    structured_llm = llm.with_structured_output(ChartSpec)

    prompt = _SYSTEM_PROMPT.format(schema=summarize_schema(df))
    spec = structured_llm.invoke(f"{prompt}\n\n使用者問題：{question}")
    return spec  # type: ignore[return-value]


def _validate_columns(df: pd.DataFrame, spec: ChartSpec) -> None:
    wanted = [c for c in (spec.x, spec.y, spec.color) if c]
    missing = [c for c in wanted if c not in df.columns]
    if missing:
        raise ValueError(
            f"圖表欄位 {missing} 不存在於資料中。可用欄位：{list(df.columns)}"
        )


_PANDAS_FREQ = {"day": "D", "month": "M", "year": "Y"}


def _apply_time_bucket(df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
    """若 spec.time_bucket 有指定，把 x 欄位解析成日期並轉為期間字串（如 2026-06）。

    無法解析成日期時，靜默放棄分桶、回傳原資料。
    """
    if spec.time_bucket == "none":
        return df

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # 非日期欄位會噴 "Could not infer format"
        parsed = pd.to_datetime(df[spec.x], errors="coerce")
    if parsed.isna().all():
        return df

    out = df.copy()
    freq = _PANDAS_FREQ[spec.time_bucket]
    # 轉成字串，避免 pandas Period 物件無法 JSON 序列化（Plotly / Gradio 需要）
    out[spec.x] = parsed.dt.to_period(freq).astype(str)
    return out


def _json_safe(data: pd.DataFrame) -> pd.DataFrame:
    """把 Plotly / Gradio 無法序列化的欄位型別（Period、Interval）轉成字串。"""
    out = data.copy()
    for col in out.columns:
        dtype = str(out[col].dtype).lower()
        if dtype.startswith(("period", "interval")):
            out[col] = out[col].astype(str)
    return out


def _aggregate(df: pd.DataFrame, spec: ChartSpec) -> tuple[pd.DataFrame, str]:
    """依 aggregation 進行 groupby，回傳 (繪圖用資料, y 欄位名稱)。"""
    group_cols = [spec.x]
    if spec.color and spec.color != spec.x:
        group_cols.append(spec.color)

    if spec.aggregation == "count" or not spec.y:
        data = df.groupby(group_cols, dropna=False).size().reset_index(name="數量")
        return data, "數量"

    if spec.aggregation in ("sum", "mean"):
        series = df.groupby(group_cols, dropna=False)[spec.y].agg(spec.aggregation)
        data = series.reset_index()
        return data, spec.y

    # aggregation == "none"：直接使用原始資料
    return df, spec.y


def build_figure(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    """依 ChartSpec 建立 Plotly 圖表（純函式、不碰網路）。"""
    _validate_columns(df, spec)
    df = _apply_time_bucket(df, spec)

    if spec.chart_type == "histogram":
        return px.histogram(_json_safe(df), x=spec.x, color=spec.color, title=spec.title)

    data, y_col = _aggregate(df, spec)
    data = _json_safe(data)

    if spec.chart_type == "line":
        fig = px.line(data, x=spec.x, y=y_col, color=spec.color, markers=True, title=spec.title)
    elif spec.chart_type == "bar":
        fig = px.bar(data, x=spec.x, y=y_col, color=spec.color, barmode="group", title=spec.title)
    elif spec.chart_type == "pie":
        fig = px.pie(data, names=spec.x, values=y_col, title=spec.title)
    elif spec.chart_type == "scatter":
        fig = px.scatter(data, x=spec.x, y=y_col, color=spec.color, title=spec.title)
    else:
        raise ValueError(f"不支援的圖表類型：{spec.chart_type}")

    fig.update_layout(margin=dict(t=60, l=40, r=20, b=40))
    return fig


def generate_chart(df: pd.DataFrame, question: str) -> tuple[go.Figure, ChartSpec]:
    """一站式：產生 ChartSpec 並繪圖。"""
    spec = suggest_chart_spec(df, question)
    fig = build_figure(df, spec)
    return fig, spec
