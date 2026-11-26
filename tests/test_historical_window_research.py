import numpy as np
import pandas as pd
import pytest

from scripts import historical_window_research as study


def test_bist_missing_future_price_does_not_shrink_signal_basket():
    dates = pd.date_range('2022-01-01', periods=21).strftime('%Y-%m-%d')
    panel = pd.MultiIndex.from_product(
        [['A', 'B'], dates], names=['symbol', 'date']).to_frame(index=False)
    panel['total_close'] = 100.
    panel['eligible_endpoint'] = True
    signal = panel.loc[panel.date.eq(dates[0])].assign(label_end=None, forward_pct=None)
    panel.loc[panel.symbol.eq('B') & panel.date.eq(dates[-1]), 'eligible_endpoint'] = False

    assert signal.symbol.tolist() == ['A', 'B']
    assert study.targets(signal, panel, 'bist').empty


def test_observed_bars_recover_features_without_filling_a_seance_or_shifting_labels():
    dates = pd.date_range('2022-01-01', periods=230, freq='B').strftime('%Y-%m-%d').tolist()
    close = 100 + np.arange(len(dates)) * .1 + np.sin(np.arange(len(dates)))
    bars = pd.DataFrame({'date': dates, 'symbol': 'A', 'close': close, 'total_close': close,
                         'open': close, 'high': close + 1, 'low': close - 1, 'volume': 100.})
    bars = bars.loc[bars.date.ne(dates[204])]
    strict = study.research.panel(bars, dates, 'bist')
    tolerant = study.gap_tolerant_bist_features(strict)
    assert pd.isna(strict.loc[strict.date.eq(dates[205]), 'trend200'].iloc[0])
    assert np.isfinite(tolerant.loc[tolerant.date.eq(dates[205]), 'trend200'].iloc[0])
    assert pd.isna(tolerant.loc[tolerant.date.eq(dates[204]), 'close'].iloc[0])
    training = study.targets(tolerant.loc[tolerant.date.eq(dates[203])], tolerant, 'bist')
    assert training.label_end.iloc[0] == dates[223]


def test_bist_flat_prices_charge_each_traded_sleeve_and_require_all_prices():
    prices = pd.DataFrame(100., index=['2022-01-04', '2022-01-05'], columns=list('ABCDEF'))
    scores = pd.DataFrame({'momentum': range(6)}, index=prices.columns)
    trial, missing = study.bist_episode((prices, prices), *prices.index, scores, 1.)
    assert not missing
    assert trial['momentum'] == pytest.approx(trial['passive'])
    assert trial['passive']['net_pct'] < trial['cash']['net_pct'] < 0.
    assert trial['passive']['fee_try'] > trial['cash']['fee_try'] > 0.

    incomplete = prices.copy()
    incomplete.iloc[-1, 0] = np.nan
    assert study.bist_episode((incomplete, prices), *prices.index, scores, 1.) == (None, ['A'])


def test_forecasts_ignore_training_labels_maturing_at_or_after_signal():
    dates = pd.date_range('2018-01-01', periods=1100, freq='B').strftime('%Y-%m-%d')
    rng = np.random.default_rng(12)
    training = pd.DataFrame(rng.normal(size=(len(dates), len(study.LEG_NAMES))), columns=study.LEG_NAMES)
    training['date'] = dates
    training['symbol'] = 'GRAM'
    training['label_end'] = training.date.shift(-20).fillna('2099-01-01')
    for column in ('forward_pct', 'ons_usd_target', 'usdtry_target'):
        training[column] = rng.normal(size=len(dates))
    testing = training.tail(1)
    old, fits = study.forecasts(training, testing, 'gold')
    changed = training.copy()
    changed.loc[changed.label_end.ge(testing.date.iloc[0]), 'forward_pct'] = 1e6

    pd.testing.assert_frame_equal(old, study.forecasts(changed, testing, 'gold')[0])
    assert all(fit['last_label'] < testing.date.iloc[0] for fit in fits.values())


def test_gold_cash_and_passive_sleeves_receive_equal_contributions():
    mids = pd.Series([100., 100., 100.], index=['2022-01-04', '2022-01-05', '2022-02-01'])
    decisions = {'2022-01-04': {'ridge-2y': 10.}, '2022-01-05': {'ridge-2y': -10.}}
    cash = study.gold_portfolio(mids, decisions, 'cash', .03)
    passive = study.gold_portfolio(mids, decisions, 'passive', .03)
    timed = study.gold_portfolio(mids, decisions, 'ridge-2y', .03)

    assert cash['contributed_try'] == passive['contributed_try'] == timed['contributed_try'] == 55_000
    assert timed['sells'] == 1
    assert timed['series'][0]['tactical_in_gold'] is True
    assert timed['series'][1]['tactical_in_gold'] is False
    assert cash['net_try'] > timed['net_try']
    assert timed['buy_tax_try'] > cash['buy_tax_try'] > 0
