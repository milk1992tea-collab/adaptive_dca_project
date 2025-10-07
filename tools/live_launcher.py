# adaptive_dca_ai/tools/live_launcher.py
import sys
import pathlib
import json

# 自動定位到 Desktop 根目錄（v_infinity 所在）
this_file = pathlib.Path(__file__).resolve()
desktop_root = this_file.parents[3]
sys.path.insert(0, str(desktop_root))

from v_infinity import orchestrator

def launch_best_strategy(json_path=None):
    json_path = json_path or pathlib.Path(__file__).parent / "outputs" / "best_strategy.json"
    if not json_path.exists():
        print(f"❌ 找不到最佳策略 JSON：{json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        candidate = json.load(f)

    print(f"🚀 啟動最佳策略 ID={candidate.get('id')} | {candidate.get('strategy')}")
    result = orchestrator.select_and_launch(candidate_bundle=candidate, mode="live", env_params={"allow_live_start": True})

    if result.get("ok") and result.get("ready_to_live"):
        print("✅ 策略已通過風控與模擬，可進入 live 模式")
    else:
        print(f"⚠️ 無法啟動 live：{result.get('reason')}")

if __name__ == "__main__":
    launch_best_strategy()