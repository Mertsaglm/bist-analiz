"""Offline portföy sınavının maliyet, stop ve katkı davranışı."""
from datetime import datetime

import pytest

from advisor.calendar import IST
from advisor.ledger import Ledger
from advisor.service import configuration
from scripts import bist_rank_replay as replay


@pytest.mark.parametrize(('open_price', 'low', 'expected'), [
    (90, 85, 90 * .9995), (105, 99, 100), (105, 100.025, 100), (105, 101, None)])
def test_stop_execution_and_single_slippage(tmp_path, open_price, low, expected):
    cfg = configuration(replay.ROOT)
    cfg['execution_phase'] = 'entry'
    ledger = Ledger(tmp_path / 'no-production-file')
    previous = '2026-10-01T11:00:00+03:00'
    ledger.add('contribution', 'fund', previous, book='tactical', amount_cents=20000)
    ledger.add('fill', 'entry', previous, book='tactical', symbol='AAA', quantity='1',
               price=110., side='BUY', notional_cents=11000, fee_cents=100, stop=100.)
    now = datetime(2026, 10, 2, 11, 45, tzinfo=IST)
    bars = {'AAA': {'open': open_price, 'low': low, 'volume': 1000}}
    replay.intraday_stops(ledger, bars, cfg, now)
    fills = ledger.account('tactical')['fills']
    if expected is None:
        assert len(fills) == 1
    else:
        assert len(fills) == 2
        assert fills[-1]['price'] == pytest.approx(expected)
        assert fills[-1]['fee_cents'] > 0


def test_flow_adjusted_drawdown_includes_first_day(tmp_path):
    rows = [{'equity_try': 90, 'contributed_try': 100},
            {'equity_try': 140, 'contributed_try': 150}]
    result = replay.performance(rows, Ledger(tmp_path / 'unused'))
    assert result['net_time_weighted_return_pct'] == pytest.approx(-10)
    assert result['max_drawdown_pct'] == pytest.approx(-10)


def test_daily_replay_reevaluates_inside_the_same_week(tmp_path, monkeypatch):
    policy = replay.portfolio
    monkeypatch.setattr(policy, '_valid', lambda *args: True)
    monkeypatch.setattr(policy, '_net_forecast', lambda *args: 0.)
    cfg = {'market': 'gold', 'execution_phase': 'entry'}
    rows = {'GRAM': {}}
    quotes = {'GRAM': {}}
    daily = Ledger(tmp_path / 'daily')
    weekly = Ledger(tmp_path / 'weekly')
    for day in (2, 3):
        now = datetime(2026, 11, day, 11, tzinfo=IST)
        policy._tactical(daily, cfg, rows, quotes, {'GRAM': 0.}, {}, now, review_daily=True)
        policy._tactical(weekly, cfg, rows, quotes, {'GRAM': 0.}, {}, now)
    assert [e['key'] for e in daily.events] == ['tactical-rebalance:2026-11-02', 'tactical-rebalance:2026-11-03']
    assert len(weekly.events) == 1


def test_training_purges_future_of_cross_sectional_reference(monkeypatch):
    import sys
    from types import SimpleNamespace

    import numpy as np
    import pandas as pd

    # The output of this spy depends on the relative targets of *all* rows.
    # A sparse stock's 20th subsequent quote can be later than its peers'.
    class TargetSpy:
        def __init__(self, **kwargs):
            pass

        def fit(self, features, targets):
            self.training_targets = targets.to_numpy()
            return self

    monkeypatch.setitem(sys.modules, 'lightgbm', SimpleNamespace(LGBMRegressor=TargetSpy))
    dates = pd.bdate_range('2020-01-01', periods=820).strftime('%Y-%m-%d')
    segments = []
    for i, symbol in enumerate(['AAA', 'BBB', 'CCC']):
        n = np.arange(len(dates))
        close = 100 + n / 20 + 3 * np.sin(n / (3 + i))
        segment = pd.DataFrame(dict(date=dates, symbol=symbol, close=close, total_close=close,
                                    high=close+1, low=close-1, volume=100))
        segments.append(segment if i < 2 else segment[n % 5 != 0])
    frame = pd.concat(segments)
    cutoff = dates[790]
    members = {'AAA', 'BBB', 'CCC'}
    _, ridge, spy, fold = replay.fit_models(frame, members, cutoff)
    changed = frame.copy()
    changed.loc[changed.date >= cutoff, ['close', 'total_close', 'high', 'low']] *= 3
    _, alternate, other, _ = replay.fit_models(changed, members, cutoff)
    assert fold['last_label_date'] < cutoff
    assert fold['last_base_label_date'] < cutoff
    assert alternate['weights'] == ridge['weights']
    np.testing.assert_array_equal(spy.training_targets, other.training_targets)
