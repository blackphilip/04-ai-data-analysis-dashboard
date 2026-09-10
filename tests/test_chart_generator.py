"""chart_generator.build_figure 的離線單元測試（不呼叫 LLM）。"""

import pandas as pd
import plotly.graph_objects as go
import pytest

from app.schemas import ChartSpec
from app.services.chart_generator import build_figure


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "小組": ["大衛", "約書亞", "大衛", "以斯帖", "約書亞"],
            "月份": ["6月", "6月", "7月", "7月", "7月"],
            "出席次數": [4, 3, 2, 5, 1],
        }
    )


def test_bar_with_sum_aggregation(df):
    spec = ChartSpec(
        chart_type="bar", x="小組", y="出席次數", aggregation="sum",
        title="各小組總出席", reasoning="比較類別總和",
    )
    fig = build_figure(df, spec)
    assert isinstance(fig, go.Figure)
    assert fig.data[0].type == "bar"
    # 大衛 = 4 + 2 = 6
    values = dict(zip(fig.data[0].x, fig.data[0].y))
    assert values["大衛"] == 6


def test_count_aggregation_without_y(df):
    spec = ChartSpec(
        chart_type="bar", x="月份", aggregation="count",
        title="各月份筆數", reasoning="計數",
    )
    fig = build_figure(df, spec)
    values = dict(zip(fig.data[0].x, fig.data[0].y))
    assert values["7月"] == 3


def test_line_chart(df):
    spec = ChartSpec(
        chart_type="line", x="月份", y="出席次數", aggregation="sum",
        title="趨勢", reasoning="時間趨勢",
    )
    fig = build_figure(df, spec)
    assert fig.data[0].type == "scatter"  # plotly line 底層是 scatter


def test_pie_chart(df):
    spec = ChartSpec(
        chart_type="pie", x="小組", y="出席次數", aggregation="sum",
        title="佔比", reasoning="組成佔比",
    )
    fig = build_figure(df, spec)
    assert fig.data[0].type == "pie"


def test_histogram_uses_raw_data(df):
    spec = ChartSpec(
        chart_type="histogram", x="出席次數",
        title="分布", reasoning="數值分布",
    )
    fig = build_figure(df, spec)
    assert fig.data[0].type == "histogram"


def test_time_bucket_month_produces_json_safe_strings():
    raw = pd.DataFrame(
        {
            "報名日期": ["2026-06-02", "2026-06-20", "2026-07-11", "2026-07-28", "2026-08-04"],
            "出席次數": [4, 3, 2, 5, 1],
        }
    )
    spec = ChartSpec(
        chart_type="line", x="報名日期", aggregation="count", time_bucket="month",
        title="各月報名數", reasoning="時間趨勢",
    )
    fig = build_figure(raw, spec)
    xs = list(fig.data[0].x)
    assert xs == ["2026-06", "2026-07", "2026-08"]
    assert all(isinstance(v, str) for v in xs)
    # 確認可被 Plotly 序列化（原本的 Period 會在此拋 TypeError）
    fig.to_json()


def test_time_bucket_ignored_when_column_not_date(df):
    spec = ChartSpec(
        chart_type="bar", x="小組", y="出席次數", aggregation="sum", time_bucket="month",
        title="x", reasoning="x",
    )
    fig = build_figure(df, spec)  # 不應拋錯
    assert fig.data[0].type == "bar"


def test_build_figure_does_not_mutate_input(df):
    before = df.copy()
    spec = ChartSpec(
        chart_type="bar", x="小組", y="出席次數", aggregation="sum",
        title="x", reasoning="x",
    )
    build_figure(df, spec)
    pd.testing.assert_frame_equal(df, before)


def test_invalid_column_raises(df):
    spec = ChartSpec(
        chart_type="bar", x="不存在的欄位", y="出席次數",
        title="x", reasoning="x",
    )
    with pytest.raises(ValueError):
        build_figure(df, spec)
