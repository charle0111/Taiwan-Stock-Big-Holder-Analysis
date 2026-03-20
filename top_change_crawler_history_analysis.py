import pandas as pd
import matplotlib.pyplot as plt
import mplcursors
import matplotlib.dates as mpl_dates
import sys
import os
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP']
plt.rcParams['axes.unicode_minus'] = False

# 檢查參數數量，sys.argv[0] 是檔名，所以長度必須大於 1
if len(sys.argv) <= 1:
    print("錯誤：請提供股票代號！")
    print("使用範例: python xxx.py 2330 2317 2454")
    sys.exit()

# ⭐ 判斷是否為 all
if sys.argv[1].lower() == "all":
    print("模式：讀取 CSV 全部股票")
    df = pd.read_csv("100plus_change_report.csv")
    # 👉 可調整要取幾筆
    stock_ids = df['stock_id'].head(3).astype(str).tolist()
    print(f"從 CSV 取得股票: {stock_ids}")
else:
    print("模式：手動輸入股票")
    # 👉 支援多股票
    stock_ids = sys.argv[1:]
    print(f"輸入股票: {stock_ids}")

print(f"本次處理股票: {stock_ids}")

def analyze_stock(stock_id):

    print(f"\n====== 處理 {stock_id} ======")

    # 1. 讀取資料
    file_path = f'/content/Taiwan-Stock-Big-Holder-Analysis/data/history/tdcc_{stock_id}_history.csv'

    # 先檢查檔案是否存在
    if not os.path.exists(file_path):
        print(f"❌ 錯誤：找不到檔案！")
        print(f"請確認路徑是否正確：{file_path}")
        print(f"提示：請先執行爬蟲程式，確認 data 資料夾內有產出 tdcc_{stock_id}_history.csv 檔案。")
        # 如果是在 script 中執行，可以使用 sys.exit() 結束
        # sys.exit() 
    else:
        # 檔案存在，嘗試用不同編碼讀取
        try:
            df = pd.read_csv(file_path, encoding='cp950')
            print(f"✅ 成功讀取資料 (cp950): {stock_id}")
        except Exception:
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
                print(f"✅ 成功讀取資料 (utf-8): {stock_id}")
            except Exception as e:
                print(f"❌ 檔案讀取失敗：可能是格式或編碼錯誤。")
                print(f"詳細錯誤訊息: {e}")

    # --- 徹底重新對齊欄位，動態配對欄位名稱 ---
    # 例如可能欄位：date, 持股分級, 人數, 股數, 占集保庫存數比例, 占集保庫存數比例_累計

    # 移除欄位名稱空格
    df.columns = [c.strip() for c in df.columns]

    # 動態尋找欄位
    col_date = next((c for c in df.columns if 'date' in c.lower()), df.columns[0])
    col_level_str = next((c for c in df.columns if '持股' in c or '級' in c), None)
    col_count_str = next((c for c in df.columns if '人數' in c or '股東' in c), None)
    col_percent_str = next((c for c in df.columns if '占集保庫存數比例' in c or '比例' in c), None)

    if col_level_str is None or col_count_str is None or col_percent_str is None:
        raise ValueError(f"找不到必要欄位，請確認 CSV 欄位名稱: {list(df.columns)}")

    # --- 核心清理邏輯 ---

    # 1. 排除「合計」與「差異調整」列 (避免數字被干擾)
    df = df[~df[col_level_str].astype(str).str.contains('合計|調整|合計')]

    # 2. 處理分級：提取區間下限完整數值
    # 範例："1,000,001以上" => 1000001；"400,001-600,000" => 400001

    def extract_level(value):
        s = str(value).replace(',', '').strip()
        if '以上' in s:
            s = s.split('以上')[0]
        if '-' in s:
            s = s.split('-')[0]
        m = pd.to_numeric(s, errors='coerce')
        return m if pd.notna(m) else 0

    # 以下限成為數值基準
    level_lower = df[col_level_str].astype(str).apply(extract_level)
    df['level_num'] = level_lower

    # 3. 處理人數與比例：移除逗號、空白，強制轉數字
    def force_numeric(series):
        return pd.to_numeric(series.astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)

    df['clean_count'] = force_numeric(df[col_count_str])
    df['clean_percent'] = force_numeric(df[col_percent_str])

    # 4. 轉換日期
    df[col_date] = pd.to_datetime(df[col_date].astype(str), errors='coerce')

    # 若有空值則切掉
    df = df.dropna(subset=[col_date])

    # 去重（避免重複紀錄造成百分比超過100）
    df = df.drop_duplicates(subset=[col_date, col_level_str, col_count_str, col_percent_str, 'stock_id'])

    # --- 計算分析數據 ---
    # 100張以上 = 100,001 shares
    # 400張以上 = 400,001 shares
    # 1000張以上 = 1,000,001 shares
    analysis_df = pd.DataFrame()
    analysis_df['100張以上(%)'] = df[df['level_num'] >= 100001].groupby(col_date)['clean_percent'].sum()
    analysis_df['400張以上(%)'] = df[df['level_num'] >= 400001].groupby(col_date)['clean_percent'].sum()
    analysis_df['1000張以上(%)'] = df[df['level_num'] >= 1000001].groupby(col_date)['clean_percent'].sum()
    # 另計「人數佔比」
    total_people = df.groupby(col_date)['clean_count'].sum()
    analysis_df['100張以上(人數%)'] = (df[df['level_num'] >= 10].groupby(col_date)['clean_count'].sum() / total_people * 100).fillna(0)
    analysis_df['400張以上(人數%)'] = (df[df['level_num'] >= 12].groupby(col_date)['clean_count'].sum() / total_people * 100).fillna(0)
    analysis_df['1000張以上(人數%)'] = (df[df['level_num'] >= 15].groupby(col_date)['clean_count'].sum() / total_people * 100).fillna(0)
    analysis_df['總股東人數'] = total_people

    analysis_df = analysis_df.sort_index()

    # 先去除重複資料，確保沒有 double count
    analysis_df = analysis_df[~analysis_df.index.duplicated(keep='last')]

    # 100% 校正與數據合理性處理
    for col in ['1000張以上(%)', '400張以上(%)', '100張以上(%)']:
        if (analysis_df[col] > 100).any():
            print(f"警告：{col} 出現超過100%的值，將自動調整上限為100%")
        analysis_df[col] = analysis_df[col].clip(upper=100)

    # 確保階層關係：1000 <= 400 <= 100
    analysis_df['400張以上(%)'] = analysis_df[['400張以上(%)', '1000張以上(%)']].max(axis=1)
    analysis_df['100張以上(%)'] = analysis_df[['100張以上(%)', '400張以上(%)']].max(axis=1)

    # 針對你給的日期 (2026-03-06, 2026-03-13) 顯示內容
    for d in ['2026-03-06', '2026-03-13']:
        dt = pd.to_datetime(d)
        if dt in analysis_df.index:
            row = analysis_df.loc[dt]
            row = row.rename({
                '100張以上(%)': '100張以上(%)',
                '400張以上(%)': '400張以上(%)',
                '1000張以上(%)': '1000張以上(%)'
            })
            print(f"\n>> {d} :")
            print(row)
            if '1000張以上(%)' in analysis_df.columns:
                row_400_999 = row['400張以上(%)'] - row['1000張以上(%)']
                print(f"400~999張以上(%) = {row_400_999:.2f}")
        else:
            print(f"\n>> {d} 沒有找到資料")


    if analysis_df['100張以上(%)'].sum() == 0:
        print("\n[錯誤]：比例總和仍為 0。請檢查 CSV 第 5 欄 (索引 4) 是否真的是比例數字？")
        print("已計算欄位:\n", analysis_df.columns.tolist())
    else:
        # --- 繪圖 ---
        plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP'] 
        plt.rcParams['axes.unicode_minus'] = False # 解決負號顯示問題

        fig, ax1 = plt.subplots(figsize=(12, 7))

        ax1.plot(analysis_df.index, analysis_df['100張以上(%)'], label='100張以上大戶(總%)', color='green', marker='s')
        ax1.plot(analysis_df.index, analysis_df['400張以上(%)'], label='400張以上大戶(總%)', color='red', marker='o')
        
        ax1.set_ylabel('持股比例 (%)')
        ax1.set_ylim(analysis_df['400張以上(%)'].min() - 2, analysis_df['100張以上(%)'].max() + 2)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')

        ax2 = ax1.twinx()
        ax2.bar(analysis_df.index, analysis_df['總股東人數'], alpha=0.1, color='blue', label='總人數')
        ax2.set_ylabel('總人數')

        # 互動點擊顯示 x/y 值
        cursor = mplcursors.cursor([ax1.lines[0], ax1.lines[1]], hover=False)

        @cursor.connect("add")
        def on_add(sel):
            x, y = sel.target
            date = mpl_dates.num2date(x).strftime('%Y-%m-%d')
            sel.annotation.set_text(f"{date}\n{y:.2f}%")

        # ⭐ 每檔股票存不同檔名
        output_file = f'analysis_{stock_id}.png'
        plt.title(f'{stock_id} 籌碼分析')
        plt.savefig(output_file, dpi=300)
        plt.close()

        print(f"✅ 已輸出: {output_file}")
        plt.show()
for stock_id in stock_ids:
    analyze_stock(stock_id)

