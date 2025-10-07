import subprocess
import os

# 專案目錄（請依實際路徑修改）
BASE_DIR = r"C:\Users\unive\Desktop\v_infinity\adaptive_dca_ai"

def run_command(cmd: str):
    print(f"\n[執行] {cmd}")
    subprocess.run(cmd, shell=True, cwd=BASE_DIR)

if __name__ == "__main__":
    print("=== 一鍵執行：優化 → 模擬 → 檢視 ===")

    # Step 1: 優化策略
    run_command("python optimize_strategy.py")

    # Step 2: 實盤模擬
    run_command("python run_live_strategy.py")

    # Step 3: 檢視結果
    run_command("python view_results.py")

    print("\n=== 全部流程完成 ===")