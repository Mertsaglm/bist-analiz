"""Aynı tarihsel sınavda doğrudan log-gram ve uzmanlaşmış bileşen tahminleri."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from advisor import history, learning, specialized
from advisor.ledger import canonical
from scripts import forecast_research as research

LEGS = {'ons_usd': 'ons_', 'usdtry': 'usdtry_'}


def fit_fold(training, testing, *, audit_horizon=None):
    names = learning.FEATURES + specialized.GOLD_LEGS

    def ridge(target, features):
        fitted = learning.fit(training.assign(forward_pct=target), 20, features, 126)
        return learning.predict(fitted, testing)

    direct = ridge(100 * np.log1p(training.forward_pct / 100), names)
    combined = np.zeros(len(testing))
    full = np.zeros(len(testing))
    result = testing[['date', 'forward_pct']].copy()
    for leg, prefix in LEGS.items():
        key = leg + '_target'
        features = [name for name in specialized.GOLD_LEGS if name.startswith(prefix)]
        model = ridge(training[key], features)
        combined += model
        full += ridge(training[key], names)
        result[key] = 100 * np.expm1(testing[key] / 100)
        result[leg] = 100 * np.expm1(model / 100)
    if audit_horizon is not None:
        leg = 'usdtry'
        result['training-mean-log'] = 100 * np.expm1(training.usdtry_target.mean() / 100)
        for window in (20, 60):
            trailing = testing[f'{leg}_momentum{window}'] / 100
            result[f'drift-{window}'] = 100 * np.expm1(np.log1p(trailing) * audit_horizon / window)
    return result.assign(zero=0., direct_log=100 * np.expm1(direct / 100),
                         specialist=100 * np.expm1(combined / 100),
                         full_components=100 * np.expm1(full / 100))


def evaluate(frame, schedule, *, audit=False):
    sessions = frame.date.tolist()
    if (schedule['market'] != 'gold' or schedule['asof'] != sessions[-1]
            or schedule['source_sha256'] != research.source_digest(frame, sessions)):
        raise ValueError('Önceki altın sınavının kaynak kesiti uyuşmuyor.')
    features = research.panel(frame, sessions, 'gold')

    def error(prediction, actual):
        delta = prediction - actual
        return {'mae_pct': float(delta.abs().mean()), 'rmse_pct': float(np.sqrt((delta ** 2).mean()))}

    result = {}
    for horizon, prior in schedule['horizons'].items():
        rows = research.labeled(features, 'gold', int(horizon), 1)
        test_dates = {row['date'] for row in prior['coverage']}
        outputs = []
        for fold in prior['test_folds']:
            training = rows.loc[rows.label_end.lt(fold['start'])]
            dates = training.date.unique()[-research.TRAIN_WINDOW:]
            training = training.loc[training.date.ge(dates[0])]
            testing = rows.loc[rows.date.between(fold['start'], fold['end']) & rows.date.isin(test_dates)]
            if not (len(training) == fold['train_rows'] and len(testing) == fold['test_rows']
                    and training.label_end.max() == fold['train_label_end']):
                raise ValueError('Eşleşen katlama bulunamadı.')
            outputs.append(fit_fold(training, testing, audit_horizon=int(horizon) if audit else None))
        predictions = pd.concat(outputs, ignore_index=True)
        if set(predictions.date) != test_dates or not predictions.date.is_unique:
            raise ValueError('Test tarihleri önceki çalışmayla eşleşmiyor.')
        result[horizon] = {
            'rows': len(predictions), 'folds': len(outputs),
            'gram': {name: error(predictions[name], predictions.forward_pct)
                     for name in ('zero', 'direct_log', 'specialist', 'full_components')},
            'legs': {name: {model: error(predictions[model], predictions[name + '_target'])
                            for model in ('zero', name)} for name in LEGS},
            'equivalence_max_delta_pct': float((predictions.direct_log - predictions.full_components).abs().max()),
        }
        if audit:
            controls = ('training-mean-log', 'drift-20', 'drift-60')
            hybrids = {'zero-ons-' + pick: predictions[pick] for pick in ('usdtry', *controls)}
            hybrids['ridge-ons-zero-kur'] = predictions.ons_usd
            result[horizon]['gram'].update({name: error(values, predictions.forward_pct)
                                            for name, values in hybrids.items()})
            result[horizon]['legs']['usdtry'].update({
                model: error(predictions[model], predictions.usdtry_target) for model in controls})
    return {'market': 'gold', 'asof': schedule['asof'], 'source_sha256': schedule['source_sha256'],
            'first_test_date': schedule['first_test_date'], 'last_test_date': schedule['last_test_date'],
            'horizons': result, 'economic_claim': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--schedule', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit', action='store_true', help='Hibrit ve geçmiş drift rakiplerini de ölç.')
    args = parser.parse_args()
    schedule = json.loads(args.schedule.read_text())
    with history.connection(research.ROOT, 'gold', args.database) as con:
        frame = history.load(con, 'gold', schedule['asof'])
    result = evaluate(frame, schedule, audit=args.audit)
    with args.output.open('x', encoding='utf-8') as out:
        out.write(canonical(result) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
