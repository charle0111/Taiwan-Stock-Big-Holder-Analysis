import os
import re
import sys
from pathlib import Path
import pandas as pd

# --- 股票名稱對照表 ---
def get_stock_name_map(base_dir):
    file_name = base_dir / "data" / "stock_list.csv"

    if file_name.exists():
        print(f"✅ 成功載入本地對照表 ({file_name})")
        df = pd.read_csv(file_name, dtype={'stock_id': str}, encoding='utf_8_sig')
        return dict(zip(df['stock_id'], df['stock_name']))
    else:
        print(f"⚠️ 找不到 {file_name}，將僅顯示代號。")
        return {}

# --- 遞迴找最新兩個檔案 ---
def find_latest_two_stock_dist_files(folder):
    pattern = re.compile(r"stock_dist_(\d{8})\.csv")
    matched_files = []

    for root, dirs, files in os.walk(folder):
        for file in files:
            match = pattern.match(file)
            if match:
                date_str = match.group(1)
                full_path = Path(root) / file
                matched_files.append((date_str, full_path))

    matched_files.sort(reverse=True)
    return [f[1] for f in matched_files[:2]]

# --- 讀取並計算統計 ---
def load_and_compute_stats(file_path):
    df = None

    for enc in ['utf_8_sig', 'cp950', 'utf-8', 'big5']:
        try:
            df = pd.read_csv(file_path, encoding=enc, dtype={'stock_id': str})
            break
        except:
            continue

    if df is None:
        print(f"❌ 無法讀取 {file_path}")
        return None

    df.columns = [c.strip() for c in df.columns]

    col_stock = next((c for c in df.columns if 'stock_id' in c or '證券代號' in c), 'stock_id')
    col_level = next((c for c in df.columns if '持股分級' in c), '持股分級')
    col_shares = next((c for c in df.columns if '持有股數' in c and '比例' not in c), '持有股數')

    df[col_shares] = pd.to_numeric(df[col_shares].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df[col_level] = pd.to_numeric(df[col_level], errors='coerce')

    totals = df[df[col_level] == 17].set_index(col_stock)[col_shares]

    def sum_range(low, high):
        return df[df[col_level].between(low, high)].groupby(col_stock)[col_shares].sum()

    s100 = sum_range(10, 15)
    s400 = sum_range(12, 15)
    s1000 = sum_range(15, 15)

    res = pd.DataFrame({
        '100plus': (s100 / totals * 100),
        '400plus': (s400 / totals * 100),
        '1000plus': (s1000 / totals * 100)
    }).fillna(0)

    return res

# --- 主程式 ---
def main():
    # 📌 判斷執行目錄（支援 Colab / 本機）
    if "__file__" in globals():
        base_dir = Path(__file__).parent
    else:
        # Colab fallback（你可以改成你的專案路徑）
        base_dir = Path("/content/Taiwan-Stock-Big-Holder-Analysis")

    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else base_dir

    print(f"📂 搜尋目錄: {folder}")

    files = find_latest_two_stock_dist_files(folder)

    if len(files) < 2:
        print(f"❌ 在 {folder} 找不到足夠的 stock_dist_YYYYMMDD.csv 檔案")
        return

    latest_file, prev_file = files[0], files[1]

    print(f"📊 比較基準: {prev_file.name} -> 最新: {latest_file.name}")

    curr_stats = load_and_compute_stats(latest_file)
    prev_stats = load_and_compute_stats(prev_file)

    if curr_stats is None or prev_stats is None:
        print("❌ CSV 讀取失敗")
        return

    merged = curr_stats.join(prev_stats, lsuffix='_curr', rsuffix='_prev')

    merged['diff_100plus'] = merged['100plus_curr'] - merged['100plus_prev']
    merged['diff_400plus'] = merged['400plus_curr'] - merged['400plus_prev']
    merged['diff_1000plus'] = merged['1000plus_curr'] - merged['1000plus_prev']

    # 股票名稱
    name_map = get_stock_name_map(base_dir)

    merged = merged.reset_index()
    merged.rename(columns={'index': 'stock_id'}, inplace=True)
    merged['股票名稱'] = merged['stock_id'].map(name_map).fillna("未知")

    # 排序
    result = merged.sort_values('diff_100plus', ascending=False)

    # 顯示前20名
    display_cols = ['stock_id', '股票名稱', '100plus_prev', '100plus_curr', 'diff_100plus']
    output = result[display_cols].head(20).copy()

    for col in ['100plus_prev', '100plus_curr', 'diff_100plus']:
        output[col] = output[col].map("{:.2f}%".format)

    print("\n=== 100張以上大戶比例增加前 20 名 ===")
    print(output.to_string(index=False))

    # 輸出 CSV
    output_file = base_dir / "100plus_change_report.csv"
    result.to_csv(output_file, encoding='utf_8_sig', index=False)

    print(f"\n📁 完整結果已存至: {output_file.resolve()}")

# --- 執行 ---
if __name__ == '__main__':
    main()
