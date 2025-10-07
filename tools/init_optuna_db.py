# adaptive_dca_ai/tools/init_optuna_db.py
import optuna
import pathlib

def init_study():
    db_path = pathlib.Path(__file__).resolve().parents[1] / "data" / "optuna_trials.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    study = optuna.create_study(
        study_name="va_al_study",
        storage=f"sqlite:///{db_path}",
        direction="maximize"
    )
    print(f"✅ Study 已建立：va_al_study\n📁 資料庫位置：{db_path}")

if __name__ == "__main__":
    init_study()