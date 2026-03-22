import requests
import pandas as pd
from io import StringIO
import datetime

def crawl():
    
    # 將網站回傳資料轉到 read_csv 解析，加入 headers 的功能為防止反爬蟲辨識，官方有時會擋 
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_1\
    0_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'} 
    res = requests.get("https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5", headers=headers)
    df = pd.read_csv(StringIO(res.text))
    df = df.astype(str)
    df = df.rename(columns={
        '證券代號': 'stock_id',
        '股數': '持有股數', '占集保庫存數比例%': '占集保庫存數比例'
    })
    
    # 移除「公債」相關的id
    debt_id = list(set([i for i in df['stock_id'] if i[0] == 'Y']))
    df = df[~df['stock_id'].isin(debt_id)]
    
    # 官方有時會有不同格式誤傳，做例外處理
    if '占集保庫存數比例' not in df.columns:
        df = df.rename(columns={'佔集保庫存數比例%': '占集保庫存數比例'})
        
    # 持股分級=16時，資料都為0，要拿掉
    df = df[df['持股分級'] != '16']
    
    # 資料轉數字
    float_cols = ['人數', '持有股數', '占集保庫存數比例']
    df[float_cols] = df[float_cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))
    
    # 抓表格上的時間資料做處理
    df['date'] = datetime.datetime.strptime(df[df.columns[0]][0], '%Y%m%d')
    
    #只要第二層欄位名稱
    df = df.drop(columns=df.columns[0])
    
    # 索引設置 unique index
    df = df.set_index(['stock_id', 'date', '持股分級'])
    return df

# 執行爬蟲
df = crawl()

# 儲存為 CSV (最常用)
import os

# 從資料中取日期
data_date = df.index.get_level_values('date')[0]
data_date_str = data_date.strftime("%Y%m%d")

year = data_date_str[:4]

# 建立資料夾
folder = f"data/{year}"
os.makedirs(folder, exist_ok=True)

# 存檔（改用資料日期）
df.to_csv(f"{folder}/stock_dist_{data_date_str}.csv", encoding='utf_8_sig')

print("存檔完成！")
