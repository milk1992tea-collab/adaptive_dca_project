from pathlib import Path
import json

# 指向 configs/strategy_params_list.json
PARAMS_FILE = Path(__file__).parent.parent / "configs" / "strategy_params_list.json"

def main():
    print("Looking for:", PARAMS_FILE.resolve())  # 印出實際路徑
    try:
        with open(PARAMS_FILE, "r", encoding="utf-8") as f:
            params_list = json.load(f)
        print("✅ 檔案讀取成功！內容如下：")
        for i, params in enumerate(params_list, start=1):
            print(f"組合 {i}: {params}")
    except FileNotFoundError:
        print("❌ 找不到檔案，請確認路徑與檔名是否正確")
    except json.JSONDecodeError as e:
        print("❌ JSON 格式錯誤:", e)

if __name__ == "__main__":
    main()