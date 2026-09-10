"""data_loader 的離線單元測試（不需要 API 金鑰）。"""

import pandas as pd
import pytest

from app.data_loader import load_dataframe, summarize_schema


def _write(path, text, encoding):
    path.write_bytes(text.encode(encoding))
    return str(path)


def test_load_utf8_csv(tmp_path):
    csv_path = _write(tmp_path / "d.csv", "姓名,分數\n小明,90\n小華,85\n", "utf-8")
    df = load_dataframe(csv_path)
    assert df.shape == (2, 2)
    assert list(df.columns) == ["姓名", "分數"]
    assert df["分數"].sum() == 175


def test_load_big5_csv_fallback(tmp_path):
    csv_path = _write(tmp_path / "big5.csv", "小組,出席\n大衛,3\n約書亞,5\n", "cp950")
    df = load_dataframe(csv_path)
    assert list(df.columns) == ["小組", "出席"]
    assert set(df["小組"]) == {"大衛", "約書亞"}


def test_column_names_are_stripped(tmp_path):
    csv_path = _write(tmp_path / "s.csv", " a , b \n1,2\n", "utf-8")
    df = load_dataframe(csv_path)
    assert list(df.columns) == ["a", "b"]


def test_unsupported_format_raises(tmp_path):
    bad = tmp_path / "note.txt"
    bad.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError):
        load_dataframe(str(bad))


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_dataframe("no_such_file.csv")


def test_utf8_bom_csv_strips_bom_from_first_column(tmp_path):
    # 模擬 Excel 另存的 UTF-8 with BOM 檔案
    csv_path = _write(tmp_path / "bom.csv", "姓名,分數\n小明,90\n", "utf-8-sig")
    df = load_dataframe(csv_path)
    assert list(df.columns) == ["姓名", "分數"]  # 第一欄不應帶著


def test_bundled_sample_csv_loads():
    import os

    sample = os.path.join(
        os.path.dirname(__file__), "..", "sample_data", "church_activity_signups.csv"
    )
    df = load_dataframe(sample)
    assert list(df.columns) == ["姓名", "活動名稱", "報名日期", "出席次數", "小組"]
    assert len(df) == 42


def test_summarize_schema_mentions_columns_and_rowcount():
    df = pd.DataFrame({"組別": ["A", "B", "A"], "值": [1, 2, 3]})
    summary = summarize_schema(df)
    assert "3 列" in summary
    assert "組別" in summary and "值" in summary
