import pandas as pd
import pytest

from scripts.bist_market_target_audit import market_target


def test_market_target_keeps_exact_end_and_excludes_zero_volume():
    sessions = ['2024-04-08', '2024-04-09', '2024-04-15', '2024-04-16']
    frame = pd.DataFrame({'symbol': ['A', 'A', 'A', 'B', 'B'],
                          'date': [sessions[0], sessions[2], sessions[3], sessions[0], sessions[1]],
                          'total_close': [100., 120., 130., 100., 112.], 'volume': [1, 1, 1, 1, 0]})
    actual = market_target(frame, sessions, 1)
    assert actual.loc[0, 'label_end'] == sessions[1]
    assert pd.isna(actual.loc[0, 'forward_pct'])
    assert actual.loc[1, 'forward_pct'] == pytest.approx(100 / 12)
    assert pd.isna(actual.loc[3, 'forward_pct'])
