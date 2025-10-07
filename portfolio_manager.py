class PortfolioManager:
    def __init__(self, max_positions=10, mode="replace", trigger="sharpe"):
        """
        max_positions: 最多持倉數量
        mode: "replace"（替換最差持倉）或 "ignore"（忽略新訊號）
        trigger: 替換依據，可選 "sharpe", "total_pnl", "drawdown"
        """
        self.max_positions = max_positions
        self.mode = mode
        self.trigger = trigger
        self.positions = {}  # key = symbol, value = metrics dict

    def can_enter(self, symbol, metrics):
        """
        判斷是否可進場，並根據模式更新持倉
        """
        if symbol in self.positions:
            return False  # 已持有，不重複進場

        if len(self.positions) < self.max_positions:
            self.positions[symbol] = metrics
            return True  # 空位可進場

        if self.mode == "ignore":
            return False  # 滿倉且保守模式，忽略新訊號

        # 替換模式：找出最差持倉
        worst = self.find_worst_position()
        if self.is_better(metrics, self.positions[worst]):
            del self.positions[worst]
            self.positions[symbol] = metrics
            return True
        return False

    def find_worst_position(self):
        """
        根據 trigger 找出最差持倉
        """
        if self.trigger == "sharpe":
            return min(self.positions, key=lambda k: self.positions[k]["sharpe_ratio"])
        elif self.trigger == "total_pnl":
            return min(self.positions, key=lambda k: self.positions[k]["total_pnl"])
        elif self.trigger == "drawdown":
            return max(self.positions, key=lambda k: self.positions[k]["max_drawdown"])
        else:
            raise ValueError("Unknown trigger")

    def is_better(self, new, old):
        """
        判斷新策略是否優於舊持倉
        """
        if self.trigger == "sharpe":
            return new["sharpe_ratio"] > old["sharpe_ratio"]
        elif self.trigger == "total_pnl":
            return new["total_pnl"] > old["total_pnl"]
        elif self.trigger == "drawdown":
            return new["max_drawdown"] < old["max_drawdown"]
        else:
            return False

    def get_current_positions(self):
        return list(self.positions.keys())

    def reset(self):
        self.positions = {}# BEGIN AUTOPATCH: enforce max positions
MAX_POSITIONS = 10

def enforce_max_positions(current_positions, candidate_list):
    """
    current_positions: list of symbols currently held
    candidate_list: ordered list of candidate symbols (highest priority first)
    returns: trimmed candidate_list that fits into available slots
    """
    free_slots = MAX_POSITIONS - len(current_positions)
    if free_slots <= 0:
        return []
    return candidate_list[:free_slots]
# END AUTOPATCH
