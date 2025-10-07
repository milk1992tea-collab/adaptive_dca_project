# adaptive_dca_ai/tools/compare_candidates.py
import sys
import pathlib

# 自動定位到 Desktop 根目錄（v_infinity 所在）
this_file = pathlib.Path(__file__).resolve()
desktop_root = this_file.parents[3]
sys.path.insert(0, str(desktop_root))

from v_infinity import orchestrator
import matplotlib.pyplot as plt
import pandas as pd
import os
import json

def compare_top_k(
    k=5,
    dataset_path=None,
    sort_by="sharpe",
    save_csv=True,
    save_png=True,
    save_json=True,
    output_dir=None
):
    tops = orchestrator.get_top_k_candidates(k)
    results = []
    for c in tops:
        sim = orchestrator.select_and_launch(candidate_bundle=c, mode="sandbox", dataset_path=dataset_path)
        if sim.get("ok"):
            s = sim["sim"]
            results.append({
                "id": c["id"],
                "strategy": c.get("strategy_name", "unknown"),
                "pnl": s["pnl"],
                "sharpe": s["sharpe"],
                "maxdd": s["maxdd"],
                "equity": s.get("equity", []),
                "trial_id": c.get("raw_row", {}).get("trial_id"),
                "created_at": c.get("created_at"),
            })

    results = sorted(results, key=lambda x: x.get(sort_by, 0.0), reverse=True)
    best = results[0] if results else None

    print(f"\n📊 Top {len(results)} strategies sorted by {sort_by}:\n")
    for r in results:
        mark = "⭐" if r is best else "  "
        print(f"{mark} ID={r['id']} | Trial={r['trial_id']} | {r['strategy']} | PnL={r['pnl']:.2f} | Sharpe={r['sharpe']:.2f} | MaxDD={r['maxdd']:.2f}")

    # 儲存報表
    outdir = output_dir or os.path.join(pathlib.Path(__file__).parent, "outputs")
    os.makedirs(outdir, exist_ok=True)

    if save_csv and results:
        df = pd.DataFrame(results).drop(columns=["equity"])
        csv_path = os.path.join(outdir, "strategy_comparison.csv")
        df.to_csv(csv_path, index=False)
        print(f"\n📁 CSV saved to: {csv_path}")

    # 儲存最佳策略為 JSON
    if save_json and best:
        json_path = os.path.join(outdir, "best_strategy.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(best, f, indent=2)
        print(f"📦 Best strategy saved to: {json_path}")

    # 畫圖並儲存
    if results:
        plt.figure(figsize=(10,6))
        for r in results:
            label = f"{r['strategy']} (ID {r['id']})"
            if r is best:
                label += " ⭐"
            plt.plot(r["equity"], label=label)
        plt.title(f"Equity Curves of Top {len(results)} Strategies")
        plt.xlabel("Steps")
        plt.ylabel("Equity")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        if save_png:
            png_path = os.path.join(outdir, "equity_curves.png")
            plt.savefig(png_path)
            print(f"🖼️ PNG saved to: {png_path}")

        plt.show()

    return results, best

# GUI 按鈕可呼叫這個
def launch_gui_comparison():
    compare_top_k(k=5)

if __name__ == "__main__":
    compare_top_k(k=5)