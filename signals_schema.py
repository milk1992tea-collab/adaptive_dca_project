def valid_signal(s):\n    try:\n        return all(k in s for k in ('symbol','timeframe','strategy'))\n    except: return False
