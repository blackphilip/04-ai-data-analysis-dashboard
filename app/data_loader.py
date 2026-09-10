"""資料載入與結構摘要工具。

負責把使用者上傳的 CSV / Excel 轉成 pandas DataFrame，
並產生一份給 LLM 閱讀的欄位結構摘要（analysis_agent 與 chart_generator 共用）。
"""

from __future__ import annotations

import os

import pandas as pd

# CSV 常見編碼，依序嘗試。
# utf-8-sig 放第一：能同時正確讀取「含 BOM」與「不含 BOM」的 UTF-8，
# 且會自動吃掉 BOM，避免第一個欄名帶著 ﻿。
# cp950 / big5 對應中文 Windows／舊版 Excel 另存的檔案。
_CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp950", "big5")

_EXCEL_SUFFIXES = (".xlsx", ".xls", ".xlsm")


def load_dataframe(path: str) -> pd.DataFrame:
    """讀取指定路徑的表格檔案並回傳 DataFrame。

    支援 .csv / .xlsx / .xls / .xlsm。CSV 會自動嘗試多種編碼，
    以相容中文 Excel 匯出的 Big5 檔案。
    """
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"找不到檔案：{path}")

    suffix = os.path.splitext(path)[1].lower()

    if suffix in _EXCEL_SUFFIXES:
        df = pd.read_excel(path)
    elif suffix == ".csv":
        df = _read_csv_with_fallback(path)
    else:
        raise ValueError(f"不支援的檔案格式：{suffix}，請上傳 CSV 或 Excel 檔。")

    if df.empty:
        raise ValueError("檔案內容為空，請確認資料是否正確。")

    # 清理欄名前後空白，避免 LLM 產生的欄位名稱對不上
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _read_csv_with_fallback(path: str) -> pd.DataFrame:
    """依序嘗試多種編碼讀取 CSV，全部失敗才拋出錯誤。"""
    last_error: Exception | None = None
    for encoding in _CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding)
        except (UnicodeDecodeError, UnicodeError) as exc:
            last_error = exc
    raise ValueError(
        f"無法解析 CSV 編碼（已嘗試 {', '.join(_CSV_ENCODINGS)}），請另存為 UTF-8 後重試。"
    ) from last_error


def summarize_schema(df: pd.DataFrame, sample_rows: int = 3) -> str:
    """產生一份純文字的欄位結構摘要，供 LLM 理解資料。

    內容包含：總列數、每個欄位的名稱與型別、前幾列樣本資料。
    """
    lines = [f"資料共有 {len(df)} 列、{df.shape[1]} 個欄位。", "", "欄位與型別："]
    for col in df.columns:
        lines.append(f"- {col}（{df[col].dtype}）")

    lines.append("")
    lines.append(f"前 {sample_rows} 列樣本：")
    lines.append(df.head(sample_rows).to_string(index=False))
    return "\n".join(lines)
