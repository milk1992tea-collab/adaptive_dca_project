# test_multi.py
import backtester
res = backtester.backtest_multi_tf_hybrid(
    'BTC/USDT',
    higher_tf='4h',
    lower_tf='15m',
    limit=10,
    params={'short_window':10,'long_window':50,'rsi_period':14,'rsi_upper':70,'rsi_lower':30}
)
print('keys:', sorted(list(res.keys())))
print('trades:', res.get('trades'))
print('params:', res.get('params'))
if res.get('equity_curve') is not None:
    print('equity_len:', len(res.get('equity_curve')))
else:
    print('equity_curve: None')
