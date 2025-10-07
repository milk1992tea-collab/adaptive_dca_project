import subprocess
import time
import datetime

def run_command(cmd):
    print(f"[執行] {cmd}")
    subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    while True:
        today = datetime.date.today()
        print(f"\n=== {today} 自動化循環開始 ===")

        # Step 1: 重新優化策略參數
        run_command("python optimize_strategy.py")

        # Step 2: 用最新參數跑測試網實盤
        run_command("python run_live_strategy.py")

        print(f"=== {today} 循環完成，等待明天再跑 ===")

        # 等待 24 小時（86400 秒）
        time.sleep(86400)