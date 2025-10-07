import os
import pandas as pd

# 設定資料夾路徑
data_dir = r"C:\Users\unive\Desktop\v_infinity\adaptive_dca_ai\research"

# 要檢查的檔案清單
files = ["btc_usdt_1h.csv", "eth_usdt_1h.csv", "bnb_usdt_1h.csv"]

for f in files:
    path = os.path.join(data_dir, f)
    if not os.path.exists(path):
        print(f"❌ 檔案不存在: {f}")
        continue

    df = pd.read_csv(path)

    # 嘗試解析時間欄位
    time_col = None
    for col in df.columns:
        if "time" in col.lower() or "date" in col.lower():
            time_col = col
            break

    print(f"\n=== {f} ===")
    print(f"總筆數: {len(df)}")

    if time_col:
        df[time_col] = pd.to_datetime(df[time_col])
        print(f"起始時間: {df[time_col].min()}")
        print(f"結束時間: {df[time_col].max()}")

        # 計算涵蓋天數
        days = (df[time_col].max() - df[time_col].min()).days
        print(f"涵蓋天數: {days} 天")
    else:
        print("⚠️ 找不到時間欄位，請確認 CSV 格式")

    # 檢查價格欄位
    price_col = None
    for col in df.columns:
        if "close" in col.lower():
            price_col = col
            break
    if price_col:
        print(f"價格範圍: {df[price_col].min()} ~ {df[price_col].max()}")