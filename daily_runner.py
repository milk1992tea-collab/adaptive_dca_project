import subprocess
import json
import os
import time

BEST_PATH = "best_params.json"
SELECTED_PATH = "selected_strategy.json"

def load_selected():
    if os.path.exists(SELECTED_PATH):
        with open(SELECTED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def load_best():
    if os.path.exists(BEST_PATH):
        with open(BEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

if __name__ == "__main__":
    print("=== 每日自動流程開始 ===")

    # 1. 跑多策略回測
    print("\n>>> 執行 multi_backtest.py")
    subprocess.run(["python", "multi_backtest.py"])

    # 2. 讀取最新最佳策略
    new_selected = load_selected()
    old_selected = load_selected()

    if new_selected:
        print(f"\n>>> 最新最佳策略: {new_selected['selected']}")
        # 3. 判斷是否切換
        if not old_selected or new_selected["selected"] != old_selected["selected"]:
            print(">>> 策略已更新，將使用新策略")
        else:
            print(">>> 保持現有策略，不切換")

    # 4. 啟動 run_live_strategy.py
    print("\n>>> 啟動 run_live_strategy.py")
    subprocess.run(["python", "run_live_strategy.py"])

    print("\n=== 每日流程完成 ===")