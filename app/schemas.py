"""Pydantic 結構化輸出模型。

ChartSpec 是 LLM 依照使用者問題與資料結構，回傳的「圖表規格」。
程式再依此規格用 Plotly 以固定邏輯繪圖（不執行 LLM 產生的繪圖程式碼）。
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

ChartType = Literal["line", "bar", "pie", "scatter", "histogram"]
Aggregation = Literal["sum", "mean", "count", "none"]
TimeBucket = Literal["none", "day", "month", "year"]


class ChartSpec(BaseModel):
    """視覺化圖表規格。"""

    chart_type: ChartType = Field(description="圖表類型：折線 line / 長條 bar / 圓餅 pie / 散佈 scatter / 直方 histogram")
    x: str = Field(description="X 軸欄位名稱（必須是資料中實際存在的欄位）")
    y: Optional[str] = Field(default=None, description="Y 軸欄位名稱；pie 圖為數值欄位，histogram 可留空")
    color: Optional[str] = Field(default=None, description="用於分組著色的欄位名稱，不需要則留空")
    aggregation: Aggregation = Field(
        default="none",
        description="繪圖前的彙總方式：加總 sum / 平均 mean / 計數 count / 不彙總 none",
    )
    time_bucket: TimeBucket = Field(
        default="none",
        description="若 x 是日期欄位且要看時間趨勢，指定分組粒度：日 day / 月 month / 年 year；否則填 none",
    )
    title: str = Field(description="圖表標題（繁體中文）")
    reasoning: str = Field(description="一句話說明為何選擇這種圖表與欄位")
