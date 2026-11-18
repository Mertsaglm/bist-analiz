import json

import pandas as pd
import pytest

from scripts.bist_forward_trial import measure, save_once


def test_forward_trial_keeps_original_file(tmp_path):
    path = tmp_path / "trial.json"
    save_once(path, {"scores": [1]})
    with pytest.raises(FileExistsError):
        save_once(path, {"scores": [2]})
    assert json.loads(path.read_text())["trial"]["scores"] == [1]


def test_forward_trial_waits_for_all_maturity_prices():
    start, end = "2026-11-17", "2026-12-15"
    trial = dict(asof=start, maturity=end, scores=[
        dict(symbol=s, total_close=100, ridge=i, lightgbm=-i)
        for i, s in enumerate("ABC")])
    frame = pd.DataFrame([(s, start, 10) for s in "ABC"],
                         columns=["symbol", "date", "total_close"])
    assert measure(trial, frame)["status"] == "vade bekleniyor"
    frame.loc[len(frame)] = ["A", end, 8]
    assert measure(trial, frame)["missing"] == ["B", "C"]
    frame.loc[len(frame)] = ["B", end, 9]
    frame.loc[len(frame)] = ["C", end, 11]
    assert measure(trial, frame)["rank_ic"] == pytest.approx(dict(ridge=1, lightgbm=-1))
