import pandas as pd
from src import config
from src.data_loader import load_prices, filter_date_range
from src.universe import load_universe_membership
from src.signals import add_momentum_signal
from src.backtest import run_backtest
from src.metrics import compute_summary

prices = filter_date_range(load_prices())
membership = load_universe_membership()

keys = [
    'MOMENTUM_METHOD','MOMENTUM_SCORE_MODE','LOOKBACK_DAYS','EWMA_HALFLIFE_DAYS',
    'REBALANCE_WEEKDAY','N_LONG','N_SHORT','TARGET_ANNUAL_VOLATILITY','MAX_GROSS_LEVERAGE',
    'MIN_SIGNAL_PRICE','LONG_BOOK_WEIGHT','SHORT_BOOK_WEIGHT','USE_BENCHMARK_TREND_SWITCH'
]
orig = {k: getattr(config, k) for k in keys}

trials = []
for hl in [2,3,5,8,12,20]:
    for n in [10,15,20,30]:
        for lw, sw in [(1.0,0.0),(0.95,0.05),(0.9,0.1),(0.8,0.2)]:
            for tv, lev in [(0.15,1.6),(0.18,2.0),(0.22,2.5)]:
                p = {
                    'MOMENTUM_METHOD':'ewma',
                    'MOMENTUM_SCORE_MODE':'raw',
                    'EWMA_HALFLIFE_DAYS':hl,
                    'REBALANCE_WEEKDAY':4,
                    'N_LONG':n,
                    'N_SHORT':n,
                    'TARGET_ANNUAL_VOLATILITY':tv,
                    'MAX_GROSS_LEVERAGE':lev,
                    'MIN_SIGNAL_PRICE':5.0,
                    'LONG_BOOK_WEIGHT':lw,
                    'SHORT_BOOK_WEIGHT':sw,
                    'USE_BENCHMARK_TREND_SWITCH':False,
                }
                trials.append((f"ewma_h{hl}_n{n}_{int(lw*100)}_{int(sw*100)}_tv{tv}_lev{lev}", p))

rows = []
for name, p in trials:
    for k, v in p.items():
        setattr(config, k, v)
    sig = add_momentum_signal(prices)
    res = run_backtest(sig, membership=membership)
    s = compute_summary(res)
    rows.append({
        'trial': name,
        'halflife': p['EWMA_HALFLIFE_DAYS'],
        'n': p['N_LONG'],
        'lw': p['LONG_BOOK_WEIGHT'],
        'sw': p['SHORT_BOOK_WEIGHT'],
        'tv': p['TARGET_ANNUAL_VOLATILITY'],
        'lev': p['MAX_GROSS_LEVERAGE'],
        'total_return': float(s['total_return']),
        'excess_total_return': float(s['excess_total_return']),
        'annualized_return': float(s['annualized_return']),
        'sharpe_ratio': float(s['sharpe_ratio']),
        'max_drawdown': float(s['max_drawdown']),
        'annualized_volatility': float(s['annualized_volatility'])
    })

for k, v in orig.items():
    setattr(config, k, v)

out = pd.DataFrame(rows).sort_values('total_return', ascending=False)
out.to_csv('outputs/quick_param_sweep_ewma_return_first.csv', index=False)
print(out.head(20).to_string(index=False))
