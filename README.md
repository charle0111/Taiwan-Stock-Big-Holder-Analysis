# Taiwan-Stock-Big-Holder-Analysis

## 功能
- `crawler.py`：下載集保資料，儲存到 `data/<year>/stock_dist_<yyyymmdd>.csv`。
- `analysis.py`：觀察單一股票的大戶持股比例趨勢圖。
- `top_change_analysis.py`：分析所有已下載資料，列出大戶集中度變動最大的股票（預設前 10 檔）。

## 使用方式
### 1) 下載資料
```bash
python crawler.py
```

### 2) 單一股票趨勢圖
可調整 `analysis.py` 內的 `stock_id`。
```bash
python analysis.py
```

### 3) 找出大戶集中度變動最大的 10 檔
```bash
python top_change_analysis.py
```

可選參數：
- `--min-level`：大戶分級下限（預設 `12`，約 400 張以上）
- `--top-n`：輸出檔數（預設 `10`）
- `--data-glob`：資料檔案路徑樣式（預設 `data/*/*.csv`）

範例：
```bash
python top_change_analysis.py --min-level 15 --top-n 10
```
