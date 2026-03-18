from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import pandas as pd
import time
import os

# ===== 設定股票代號 =====
stock_list = ["2317", "2915", "2330", "8271", "3645"]
incremental = True

print("啟動瀏覽器")

# ✅ GitHub 必備 headless 設定
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

url = "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock"
driver.get(url)

time.sleep(3)

# ===== 取得所有日期 =====
date_select = Select(driver.find_element(By.ID, "scaDate"))
dates = [opt.get_attribute("value") for opt in date_select.options]
print("可查詢日期數:", len(dates))

for stock_id in stock_list:
    print("\n===== 處理股票：", stock_id, "=====")
    file_name = f"tdcc_{stock_id}_history.csv"

    if os.path.exists(file_name):
        try:
            old_df = pd.read_csv(file_name, encoding='utf_8_sig')
        except:
            old_df = pd.read_csv(file_name, encoding='cp950', errors='ignore')

        existing_dates = set(old_df['date'].astype(str)) if 'date' in old_df.columns else set()
        if not incremental:
            existing_dates = set()
    else:
        old_df = pd.DataFrame()
        existing_dates = set()

    to_fetch_dates = [d for d in dates if d not in existing_dates]

    if not to_fetch_dates:
        print("無更新")
        continue

    all_data = []
    headers = []

    for date in to_fetch_dates:
        print("抓取:", date)

        Select(driver.find_element(By.ID, "scaDate")).select_by_value(date)

        stock_input = driver.find_element(By.NAME, "stockNo")
        stock_input.clear()
        stock_input.send_keys(stock_id)

        driver.find_element(By.XPATH, '//*[@id="form1"]/table/tbody/tr[4]/td/input').click()
        time.sleep(2)

        tables = driver.find_elements(By.TAG_NAME, "table")
        rows = []

        for t in tables:
            r = t.find_elements(By.TAG_NAME, "tr")
            if len(r) > 10:
                rows = r
                break

        if not rows:
            print("抓不到資料:", date)
            continue

        if not headers:
            headers = [th.text.strip() for th in rows[0].find_elements(By.TAG_NAME, "th")]

        for r in rows[1:]:
            cols = [c.text.strip() for c in r.find_elements(By.TAG_NAME, "td")]
            if len(cols) >= len(headers):
                all_data.append([date] + cols[:len(headers)] + [stock_id])

    columns = ["date"] + headers + ["stock_id"]
    df = pd.DataFrame(all_data, columns=columns)

    if not old_df.empty:
        df = pd.concat([old_df, df], ignore_index=True)

    level_col = next((c for c in df.columns if '持股' in c or '級' in c), None)

    df = df.drop_duplicates(subset=['date', level_col, 'stock_id'], keep='last')

    df.to_csv(file_name, index=False, encoding='utf_8_sig')
    print("完成:", file_name)

print("關閉瀏覽器")
driver.quit()
