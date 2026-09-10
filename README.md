# 📊 AI 驅動的數據分析與圖表生成面板 (AI-Powered Data Analysis & Chart Dashboard)

> **結合 Python、LangChain Pandas Agent、Google Gemini API 與 Plotly，讓非技術人員用「一句中文」即可完成表格資料分析與互動式視覺化。**

---

## 💡 專案簡介與痛點解決

在教會、社群與中小型組織中，報名表、出席紀錄、奉獻明細等資料多以 Excel／CSV 形式散落各處。想從中取得洞察（「哪個小組最活躍？」「這季報名趨勢如何？」）往往得仰賴會寫樞紐分析或 pandas 的人，形成資料取用的門檻。

本專案建構了一套 **自然語言資料分析面板**：

1. 使用者透過 Gradio 網頁介面上傳 CSV 或 Excel 檔案，系統自動解析並顯示欄位結構與資料預覽。
2. 使用者用中文提問，**LangChain Pandas DataFrame Agent** 驅動 Gemini 自動撰寫並執行 pandas 程式碼，回傳附帶關鍵數字的中文結論。
3. 系統另以 **Structured Outputs（Pydantic `ChartSpec`）** 讓 LLM 決定最適合的圖表類型與欄位，再由程式以固定邏輯用 **Plotly** 繪製互動式圖表（折線／長條／圓餅／散佈／直方）。
4. 圖表繪製與資料分析解耦：即使某個問題無法自動繪圖，文字結論仍會正常呈現。

---

## 🛠️ 技術架構與工具 (Tech Stack)

* **Language:** Python (v3.10+)
* **Framework & UI:** Gradio (Web Dashboard、檔案上傳與事件綁定)
* **AI & LLM:** Google Gemini API (`gemini-3.1-flash-lite`)
* **Agent & Orchestration:** LangChain, LangChain Experimental (`create_pandas_dataframe_agent`), LangChain Google GenAI
* **Data & Viz:** pandas, openpyxl (Excel), Plotly Express
* **Schema & Validation:** Pydantic v2 (Structured Outputs `ChartSpec`)
* **Testing & Environment:** pytest, VS Code, Python Virtual Environment (`venv`), Git/GitHub, `python-dotenv`

---

## 🏗️ 系統運作架構圖 (Workflow)

```text
[ Gradio Web UI 上傳 CSV / Excel ]
         │
         ▼
[ data_loader：多編碼解析 (UTF-8 / Big5) → DataFrame + 結構摘要 ]
         │
         ├───────────────► [ analysis_agent ]
         │                   Pandas DataFrame Agent (LangChain Experimental)
         │                   └─► Gemini 自動撰寫並執行 pandas 程式碼
         │                        └─► 中文分析結論 (含關鍵數字)
         │
         └───────────────► [ chart_generator ]
                             (1) Gemini + Pydantic ChartSpec (Structured Output)
                             (2) build_figure()：純函式，依規格用 Plotly 繪圖
                                  └─► 互動式圖表 + 選圖理由
         │
         ▼
[ Gradio 同時渲染「文字結論」與「互動圖表」 ]
```

---

## 🚀 快速開始

```powershell
cd 04-ai-data-analysis-dashboard
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 設定金鑰：複製範例檔後填入你的 Gemini API Key
copy .env.example .env
# 編輯 .env，填入 GEMINI_API_KEY=...

# 執行離線單元測試
pytest -q

# 啟動面板（開啟終端顯示的 http://127.0.0.1:7860）
python -m app.main
```

內附 `sample_data/church_activity_signups.csv` 範例資料（UTF-8 with BOM，Excel 可直接開啟；
系統同時支援 Big5 / CP950 編碼的檔案），上傳後可直接試問：

* 「哪個小組的總出席次數最高？」
* 「各月份的報名數量趨勢如何？」
* 「各活動的平均出席次數是多少？」

---

## 📁 專案結構

```
app/
├── main.py                 # Gradio Blocks UI 與事件綁定
├── data_loader.py          # CSV/Excel 載入、欄位結構摘要（共用工具）
├── schemas.py              # Pydantic：ChartSpec
└── services/
    ├── analysis_agent.py   # LangChain Pandas Agent 包裝：NL → 中文分析結論
    └── chart_generator.py  # NL + schema → ChartSpec → Plotly Figure
tests/                      # 離線單元測試（data_loader、build_figure）
sample_data/                # 範例 CSV
```

---

## 🔒 安全性備註

LangChain Pandas Agent 會在**本機 Python 環境執行 LLM 生成的程式碼**（`allow_dangerous_code=True`）。本專案定位為「本機單人分析工具」，上傳資料不會離開你的電腦。請勿：

* 將此服務直接對外網公開；
* 載入來源不明的檔案。

圖表繪製走 `ChartSpec` 結構化規格 + 固定 `build_figure()` 邏輯，**不執行** LLM 生成的繪圖程式碼。

### 上傳檔案怎麼處理？

* 你的**原始檔案不會被移動**，程式只讀不寫。
* Gradio 會把上傳檔複製一份到專案下的 `.gradio_cache/`（已加入 `.gitignore`）。
  本專案設定 `delete_cache=(60, 3600)`：每分鐘清理、刪除逾 1 小時的暫存檔，正常 `Ctrl+C` 關閉時也會清空。
* 解析後的資料只存在**記憶體**（Gradio `State`），關掉分頁即釋放；不寫入任何資料庫。
* 若要換位置，啟動前設環境變數 `GRADIO_TEMP_DIR`；要立即清空，直接刪除 `.gradio_cache/` 資料夾即可。
* **會離開你電腦的內容**：欄位結構與少量樣本列會隨提問送到 Google Gemini API。請勿上傳含個資或機密的資料。

---

## 📄 License

MIT License — Copyright (c) 2026 C.T Chang
