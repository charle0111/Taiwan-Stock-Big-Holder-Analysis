import pandas as pd
import glob
import matplotlib.pyplot as plt

# --- 使用者設定區 ---
stock_id = "3227"

import glob
files = glob.glob("data/*/*.csv")  # 讀所有年份的 CSV

# 定義要觀察的門檻與對應的集保分級
# 100張(10級), 400張(12級), 1000張(15級)
thresholds = {
    "100張以上": 10,
    "400張以上": 12,
    "1000張以上": 15
}

# 解決中文亂碼
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # 黑體，Colab 內建
plt.rcParams['axes.unicode_minus'] = False

all_data = []

for f in files:
    try:
        df = pd.read_csv(f)
        
        # 資料清洗與型態轉換 (處理科學記號與逗號)
        df["持有股數"] = pd.to_numeric(df["持有股數"].astype(str).str.replace(',', ''), errors='coerce')
        df["持股分級"] = pd.to_numeric(df["持股分級"], errors='coerce')
        df["stock_id"] = df["stock_id"].astype(str).str.strip()

        # 篩選特定股票
        df_stock = df[df["stock_id"] == stock_id].copy()
        if df_stock.empty:
            continue

        # 1. 取得總股數 (優先取第 17 級，若無則加總 1-15 級)
        total_row = df_stock[df_stock["持股分級"] == 17]
        if not total_row.empty:
            total_shares = total_row["持有股數"].iloc[0]
        else:
            total_shares = df_stock[df_stock["持股分級"] <= 15]["持有股數"].sum()

        if total_shares == 0: continue

        # 2. 取得日期
        date_val = df_stock["date"].iloc[0]
        
        # 3. 核心邏輯：迴圈計算各個門檻的比例
        row_entry = {"date": date_val}
        for label, level in thresholds.items():
            # 大戶股數：加總 [該級別, 15級] (避開17級總計)
            big_shares = df_stock[df_stock["持股分級"].between(level, 15)]["持有股數"].sum()
            row_entry[label] = (big_shares / total_shares) * 100

        all_data.append(row_entry)

    except Exception as e:
        print(f"讀取檔案 {f} 時出錯: {e}")

# 資料排序
result = pd.DataFrame(all_data)
if result.empty:
    print("找不到相關資料，請檢查檔案路徑或 stock_id")
    exit()

result["date"] = pd.to_datetime(result["date"])
result = result.sort_values("date")

# --- 繪圖區 ---
plt.figure(figsize=(12, 7))

# 定義顏色與樣式
colors = {"100張以上": "#3498db", "400張以上": "#e67e22", "1000張以上": "#e74c3c"}
markers = {"100張以上": "o", "400張以上": "s", "1000張以上": "^"}

for label in thresholds.keys():
    plt.plot(result["date"], result[label], 
             label=label, 
             color=colors[label], 
             marker=markers[label], 
             linewidth=2, 
             markersize=6)

plt.title(f"股票 {stock_id}：大戶持股比例多線對比圖", fontsize=16, fontweight='bold')
plt.xlabel("日期", fontsize=12)
plt.ylabel("持股比例 (%)", fontsize=12)
plt.grid(True, which='both', linestyle='--', alpha=0.5)
plt.legend(title="大戶定義", loc='best')

# 優化 X 軸日期顯示 (避免擠在一起)
plt.gcf().autofmt_xdate() 

# 標註最新一週的比例在圖表上
for label in thresholds.keys():
    last_val = result[label].iloc[-1]
    plt.text(result["date"].iloc[-1], last_val, f' {last_val:.2f}%', 
             color=colors[label], va='center', fontweight='bold')

plt.tight_layout()
plt.show()
