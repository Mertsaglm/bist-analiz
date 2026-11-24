import numpy as np
import pandas as pd
import pytest

from scripts import forecast_research as research
from scripts import forecast_audit
from scripts import forecast_rank_shadow as shadow
from scripts import gold_leg_research as gold_legs


def test_bist30_research_excludes_watchlist_and_rejects_incomplete_membership():
    day = '2026-11-24'
    stocks = [dict(symbol=f'S{i}', known_at=day, effective_from=day,
                   source='fixture', reason='BIST30', active=True) for i in range(30)]
    extra = dict(stocks[0], symbol='EXTRA', reason='İzleme')
    assert research.bist_members(stocks + [extra], day) == {row['symbol'] for row in stocks}
    with pytest.raises(ValueError, match='29/30'):
        research.bist_members(stocks[1:] + [extra], day)


def test_bist_session_requires_index_or_stock_concordance_and_respects_known_holiday():
    rows = pd.DataFrame([dict(date=day, symbol=f'S{i}', close=10., volume=100)
                         for day, count in [('2026-05-18', 24), ('2026-05-19', 30),
                                            ('2026-05-20', 23), ('2026-05-21', 2)]
                         for i in range(count)])
    cfg = {'calendar': {'full_days': ['2026-05-19']}}
    assert research.bist_sessions(['2026-05-19', '2026-05-21'], rows, cfg) == [
        '2026-05-18', '2026-05-21']


def test_missing_bist_bar_does_not_move_maturity_or_reduce_expected_universe():
    dates = list(pd.bdate_range('2024-01-01', periods=240).strftime('%Y-%m-%d'))
    missing = dates[221]
    rows = []
    for index, symbol in enumerate('ABCDE'):
        for i, day in enumerate(dates):
            if symbol == 'E' and day == missing:
                continue
            close = 50 + i / 10 + np.sin(i / 6) + index
            rows.append(dict(symbol=symbol, date=day, close=close, open=close,
                             total_close=close, high=close + 1, low=close - 1, volume=100 + i))
    features = research.panel(pd.DataFrame(rows), dates, 'bist')
    subset = research.labeled(features, 'bist', 5, 5).query('date == @dates[216]')
    assert set(subset.symbol) == set('ABCD')
    assert subset.label_end.unique().tolist() == [missing]
    assert subset.forward_pct.mean() == pytest.approx(0, abs=1e-12)
    assert research.labeled(features, 'bist', 5, 6).query('date == @dates[216]').empty


def test_walk_forward_purges_entire_overlapping_dates(monkeypatch):
    dates = list(pd.bdate_range('2024-01-01', periods=10).strftime('%Y-%m-%d'))
    rows = pd.DataFrame([dict(date=day, label_end=end, symbol=symbol)
                         for day, end in zip(dates[:-2], dates[2:]) for symbol in 'AB'])
    monkeypatch.setattr(research, 'TRAIN_MIN', 2)
    seen = []

    def audit(training, testing, market, horizon):
        seen.append(set(training.date))
        assert training.label_end.max() < testing.date.min()
        assert testing.groupby('date').size().eq(2).all()
        return testing

    monkeypatch.setattr(research, 'forecast', audit)
    predicted, folds = research.walk_forward(rows, dates[4:8], 'bist', 2)
    assert seen == [set(dates[:2])]
    assert len(predicted) == 8 and folds[0]['train_label_end'] == dates[3]


def test_calibration_excludes_test_outcomes_and_requires_mature_predictions():
    dates = list(pd.bdate_range('2024-01-01', periods=132).strftime('%Y-%m-%d'))
    past = pd.DataFrame({'date': dates[:126], 'label_end': dates[2:128],
                         'forward_pct': np.arange(126) / 10, 'ridge': np.arange(126) / 20,
                         'ewma_vol': 1.})
    future = pd.DataFrame({'date': dates[128:130], 'forward_pct': [4., 6.],
                           'ridge': [2., 3.], 'ewma_vol': [.6, 1.4]})
    calibrated, fit = research.calibrate(past, future, 'gold', 20)
    changed, changed_fit = research.calibrate(past, future.assign(forward_pct=-100), 'gold', 20)
    pd.testing.assert_frame_equal(calibrated.drop(columns='forward_pct'), changed.drop(columns='forward_pct'))
    assert fit == changed_fit
    assert (calibrated['ewma-q0.1'] <= calibrated['ewma-q0.9']).all()
    past.loc[0, 'label_end'] = dates[128]
    with pytest.raises(ValueError, match='örtüşüyor'):
        research.calibrate(past, future, 'gold', 20)


def test_shadow_measure_uses_sealed_maturity_and_does_not_shrink_coverage():
    start, end, later = '2026-11-24', '2026-12-22', '2026-12-23'
    names = 'ABCDEF'
    trial = {'asof': start, 'maturity': end, 'missing_features': ['G'],
             'scores': [dict(symbol=s, **{model: i for model in shadow.MODELS})
                        for i, s in enumerate(names)]}
    frame = pd.DataFrame([dict(date=day, symbol=s, total_close=close)
                          for i, s in enumerate(names) for day, close in
                          [(start, 100), (end, 100 + i), (later, 1000)]])
    assert shadow.measure(trial, frame[frame.date == start])['status'] == 'vade bekleniyor'
    assert shadow.measure(trial, frame[~(frame.date.eq(end) & frame.symbol.eq('F'))])['missing'] == ['F']
    scored = shadow.measure(trial, frame)
    assert scored['expected'] == 6 and scored['missing_features_at_freeze'] == ['G']
    assert scored['metrics']['lightgbm-ranking'] == pytest.approx({'rank_ic': 1., 'top5_excess_pct': .5})


def test_shared_features_ridge_is_equivalent_to_direct_gram_log_model():
    generator = np.random.default_rng(42)
    names = research.learning.FEATURES + research.specialized.GOLD_LEGS
    rows = pd.DataFrame(generator.normal(size=(90, len(names))), columns=names)
    rows['date'] = pd.bdate_range('2024-01-01', periods=len(rows)).strftime('%Y-%m-%d')
    rows['symbol'] = 'GRAM'
    rows['ons_usd_target'] = rows.ons_momentum20 + rows.usdtry_trend50
    rows['usdtry_target'] = rows.usdtry_momentum20
    rows['forward_pct'] = 100 * np.expm1((rows.ons_usd_target + rows.usdtry_target) / 100)
    got = gold_legs.fit_fold(rows.iloc[:80], rows.iloc[80:])
    np.testing.assert_allclose(got.direct_log, got.full_components, atol=1e-12)
    assert not np.allclose(got.direct_log, got.specialist)


def test_gold_drift_uses_trailing_price_and_scales_horizon():
    generator = np.random.default_rng(43)
    names = research.learning.FEATURES + research.specialized.GOLD_LEGS
    rows = pd.DataFrame(generator.normal(size=(80, len(names))), columns=names)
    rows['date'] = pd.bdate_range('2024-01-01', periods=len(rows)).strftime('%Y-%m-%d')
    rows['symbol'] = 'GRAM'
    rows['ons_usd_target'] = rows.ons_momentum20
    rows['usdtry_target'] = rows.usdtry_momentum20
    rows['forward_pct'] = 100 * np.expm1((rows.ons_usd_target + rows.usdtry_target) / 100)
    test = rows.iloc[78:].assign(usdtry_momentum20=4., usdtry_momentum60=12.)
    result = gold_legs.fit_fold(rows.iloc[:78], test, audit_horizon=5)
    assert result['drift-20'].tolist() == pytest.approx([100 * (1.04 ** .25 - 1)] * 2)
    assert result['drift-60'].tolist() == pytest.approx([100 * (1.12 ** (1 / 12) - 1)] * 2)


def test_block_bootstrap_retains_a_constant_paired_difference():
    rng = np.random.default_rng(42)
    assert forecast_audit.block_interval([.75] * 20, 5, rng) == [.75, .75]
    assert forecast_audit.block_interval([0.] * 3, 5, rng) is None
