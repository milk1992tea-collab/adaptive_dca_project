import optuna
import json
import time
from typing import List, Dict, Any
from data_fetch import fetch_klines
from strategy import dca_simulate, composite_score

# 多幣種（可自行增減）
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
INTERVAL = "1"   # 1 分鐘
LIMIT = 1000     # 每幣抓 1000 根

BEST_EXPORT_PATH = "best_params.json"

def evaluate_params(step: float, base_qty: float, tp_pct: float, sl_pct: float) -> Dict[str, Any]:
    """
    在多幣種上評估參數，回傳合併績效與明細
    """
    results = []
    for sym in SYMBOLS:
        prices = fetch_klines(sym, INTERVAL, LIMIT)
        metrics = dca_simulate(
            prices=prices,
            step=step,
            base_qty=base_qty,
            take_profit_pct=tp_pct,
            stop_loss_pct=sl_pct,
            max_position_qty=1000.0
        )
        results.append({"symbol": sym, "metrics": metrics})

    # 加權整合（簡化：平均分數）
    total_score = 0.0
    for r in results:
        total_score += composite_score(r["metrics"])
    total_score /= max(len(results), 1)

    return {"score": total_score, "details": results}


def objective(trial: optuna.Trial) -> float:
    step = trial.suggest_float("step", 1.0, 20.0)                # 小步長避免空轉
    base_qty = trial.suggest_float("base_qty", 1.0, 30.0)        # 單次加倉額度（USDT 名義）
    tp_pct = trial.suggest_float("take_profit_pct", 0.01, 0.10)  # 1% ~ 10% 止盈
    sl_pct = trial.suggest_float("stop_loss_pct", -0.10, -0.01)  # -10% ~ -1% 止損

    eval_res = evaluate_params(step, base_qty, tp_pct, sl_pct)
    score = eval_res["score"]

    # 每次 trial 記錄到 trial.user_attrs（方便追蹤）
    trial.set_user_attr("details", eval_res["details"])
    return score


def export_best(study: optuna.Study):
    best = study.best_trial
    payload = {
        "params": best.params,
        "score": best.value,
        "timestamp": int(time.time()),
        "details": best.user_attrs.get("details", [])
    }
    with open(BEST_EXPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[導出] 最佳參數寫入 {BEST_EXPORT_PATH}")


class ProgressCallback:
    def __init__(self, every_n: int = 50):
        self.every_n = every_n

    def __call__(self, study: optuna.Study, trial: optuna.Trial):
        if (trial.number + 1) % self.every_n == 0:
            print(f"[進度] 已完成 {trial.number + 1} trials，暫最佳分數={study.best_value:.4f}, 參數={study.best_params}")
            export_best(study)


if __name__ == "__main__":
    # 長時間持久化（斷線可接續）
    study = optuna.create_study(
        direction="maximize",
        study_name="dca_opt_multi",
        storage="sqlite:///dca_opt_multi.db",
        load_if_exists=True
    )

    # 跑久一點（可改更大）
    study.optimize(objective, n_trials=500, callbacks=[ProgressCallback(every_n=25)])

    print("最佳參數:", study.best_params)
    print("最佳分數:", study.best_value)
    export_best(study)