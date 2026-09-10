"""AI 驅動的數據分析與圖表生成面板 — Gradio 入口。

啟動：
    python -m app.main
"""

from __future__ import annotations

import os

# 把 Gradio 上傳暫存檔集中放到專案目錄下的 .gradio_cache/（已被 .gitignore 忽略），
# 方便查看與清理；必須在 import gradio 之前設定。
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".gradio_cache")
os.environ.setdefault("GRADIO_TEMP_DIR", _CACHE_DIR)

import gradio as gr  # noqa: E402
import pandas as pd  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from app.data_loader import load_dataframe, summarize_schema  # noqa: E402
from app.services.analysis_agent import run_analysis  # noqa: E402
from app.services.chart_generator import generate_chart  # noqa: E402

load_dotenv()

API_KEY_READY = bool(os.getenv("GEMINI_API_KEY"))

EXAMPLE_QUESTIONS = [
    "哪個小組的總出席次數最高？",
    "各月份的報名數量趨勢如何？",
    "各活動的平均出席次數是多少？",
    "出席次數最多的前三位是誰？",
]


def handle_upload(file_obj):
    """處理檔案上傳：載入 DataFrame、回傳預覽與結構摘要。"""
    if file_obj is None:
        return None, None, "尚未上傳檔案。"

    try:
        df = load_dataframe(file_obj.name if hasattr(file_obj, "name") else file_obj)
    except (FileNotFoundError, ValueError) as exc:
        return None, None, f"⚠️ 讀取失敗：{exc}"

    schema_md = f"✅ 已載入 **{len(df)}** 列資料。\n\n```\n{summarize_schema(df)}\n```"
    return df, df.head(50), schema_md


def handle_analyze(df: pd.DataFrame | None, question: str):
    """執行分析與繪圖，回傳 (文字結論, 圖表, 選圖理由)。"""
    if df is None:
        return "⚠️ 請先在上方上傳 CSV 或 Excel 檔案。", None, ""

    if not (question or "").strip():
        return "⚠️ 請輸入想分析的問題。", None, ""

    answer = run_analysis(df, question)
    answer_md = f"> 🙋 **提問**：{question}\n\n### 📈 分析結論\n\n{answer}"

    try:
        fig, spec = generate_chart(df, question)
        fig.to_json()  # 提前觸發序列化，若失敗就在這裡優雅降級，而非讓 Gradio 回傳 500
        chart_types = {
            "line": "折線圖", "bar": "長條圖", "pie": "圓餅圖",
            "scatter": "散佈圖", "histogram": "直方圖",
        }
        reasoning = f"📊 **為何用{chart_types.get(spec.chart_type, spec.chart_type)}**：{spec.reasoning}"
    except Exception as exc:  # noqa: BLE001 - 圖表失敗不影響文字結論
        fig, reasoning = None, f"ℹ️ 此問題暫時無法自動繪圖（{exc}）"

    return answer_md, fig, reasoning


def build_demo() -> gr.Blocks:
    # delete_cache=(60, 3600)：每 60 秒清一次，刪除超過 1 小時的上傳暫存檔；
    # 正常關閉伺服器 (Ctrl+C) 時也會一併清空 .gradio_cache/。
    with gr.Blocks(
        title="AI 數據分析與圖表生成面板",
        delete_cache=(60, 3600),
    ) as demo:
        gr.Markdown(
            "# 📊 AI 驅動的數據分析與圖表生成面板\n"
            "上傳 CSV / Excel，用中文提問，AI 自動撰寫 pandas 分析並產生互動圖表。"
        )

        if not API_KEY_READY:
            gr.Markdown(
                "> ⚠️ **尚未偵測到 `GEMINI_API_KEY`**：請將 `.env.example` 複製為 `.env` 並填入金鑰後重新啟動。"
            )

        df_state = gr.State(value=None)

        with gr.Row():
            file_input = gr.File(
                label="上傳資料檔",
                file_types=[".csv", ".xlsx", ".xls", ".xlsm"],
            )
            schema_output = gr.Markdown(label="資料結構")

        preview_output = gr.Dataframe(label="資料預覽（前 50 列）", interactive=False)

        question_input = gr.Textbox(
            label="輸入你的問題",
            placeholder="例如：哪個小組的總出席次數最高？",
            lines=2,
        )
        gr.Examples(examples=EXAMPLE_QUESTIONS, inputs=question_input, label="範例問題")

        analyze_btn = gr.Button("🔍 開始分析", variant="primary")

        with gr.Row(equal_height=False):
            with gr.Column(scale=1):
                answer_output = gr.Markdown(
                    value="_分析結論會顯示在這裡…_",
                    container=True,
                    show_label=True,
                    label="分析結論",
                )
            with gr.Column(scale=1):
                plot_output = gr.Plot(label="圖表")
                reasoning_output = gr.Markdown()

        file_input.change(
            handle_upload,
            inputs=file_input,
            outputs=[df_state, preview_output, schema_output],
        )
        analyze_btn.click(
            handle_analyze,
            inputs=[df_state, question_input],
            outputs=[answer_output, plot_output, reasoning_output],
        )

    return demo


def main() -> None:
    build_demo().launch(theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
