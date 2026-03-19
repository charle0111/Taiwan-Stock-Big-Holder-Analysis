import os
import re
import sys
from pathlib import Path
import pandas as pd

# --- 修改：從本地 CSV 讀取股票名稱對照表 ---
def get_stock_name_map():
    file_name = "data/stock_list.csv"
    if os.path.exists(file_name):
        print(f"✅ 成功載入本地對照表 ({file_name})")
        # 強制將 stock_id 讀為字串，避免 0050 變成 50
        df = pd.read_csv(file_name, dtype={'stock_id': str}, encoding='utf_8_sig')
        return dict(zip(df['stock_id'], df['stock_name']))
    else:
        print(f"⚠️ 找不到 {file_name}，將僅顯示代號。")
        return {}

def find_latest_two_stock_dist_files(folder: str):
    pattern = re.compile(r"stock_dist_(\d{8})\.csv$")
    files = []
    for p in Path(folder).iterdir():
        m = pattern.match(p.name)
        if m and p.is_file():
            files.append((m.group(1), p))
    # 降冪排序，files[0] 是最新，files[1] 是次新
    files.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in files[:2]]

def load_and_compute_stats(file_path):
    df = None
    for enc in ['utf_8_sig', 'cp950', 'utf-8', 'big5']:
        try:
            df = pd.read_csv(file_path, encoding=enc, dtype={'stock_id': str})
            break
        except: continue
    if df is None: return None

    df.columns = [c.strip() for c in df.columns]
    col_stock = next((c for c in df.columns if 'stock_id' in c or '證券代號' in c), 'stock_id')
    col_level = next((c for c in df.columns if '持股分級' in c), '持股分級')
    col_shares = next((c for c in df.columns if '持有股數' in c and '比例' not in c), '持有股數')

    df[col_shares] = pd.to_numeric(df[col_shares].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df[col_level] = pd.to_numeric(df[col_level], errors='coerce')

    # 計算總股數 (第 17 級)
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

def main():
    # 若執行時沒給路徑，預設讀取當前資料夾 "."
    folder = sys.argv[1] if len(sys.argv) > 1 else '.'
    files = find_latest_two_stock_dist_files(folder)
    
    if len(files) < 2:
        print(f"在 {folder} 找不到足夠的 stock_dist_YYYYMMDD.csv 檔案")
        return

    latest_file, prev_file = files[0], files[1]
    print(f"比較基準: {prev_file.name} -> 最新: {latest_file.name}")

    curr_stats = load_and_compute_stats(latest_file)
    prev_stats = load_and_compute_stats(prev_file)

    # 合併兩週數據
    merged = curr_stats.join(prev_stats, lsuffix='_curr', rsuffix='_prev')
    
    # 計算百分比變化量
    merged['diff_100plus'] = merged['100plus_curr'] - merged['100plus_prev']
    merged['diff_400plus'] = merged['400plus_curr'] - merged['400plus_prev']
    merged['diff_1000plus'] = merged['1000plus_curr'] - merged['1000plus_prev']

    # 套用本地股票名稱對照表
    name_map = get_stock_name_map()
    merged = merged.reset_index()
    merged.rename(columns={'index': 'stock_id'}, inplace=True)
    merged['股票名稱'] = merged['stock_id'].map(name_map).fillna("未知")

    # 依 100張以上大戶增加比例排序
    result = merged.sort_values('diff_100plus', ascending=False)

    # 格式化輸出前 20 名
    display_cols = ['stock_id', '股票名稱', '100plus_prev', '100plus_curr', 'diff_100plus']
    output = result[display_cols].head(20).copy()
    for col in ['100plus_prev', '100plus_curr', 'diff_100plus']:
        output[col] = output[col].map("{:.2f}%".format)

    print("\n=== 100張以上大戶比例增加前 20 名 ===")
    print(output.to_string(index=False))
    
    # 輸出完整 CSV 結果
    result.to_csv('100plus_change_report.csv', encoding='utf_8_sig', index=False)
    print(f"\n完整結果已存至: {os.path.abspath('100plus_change_report.csv')}")

if __name__ == '__main__':
    main()
