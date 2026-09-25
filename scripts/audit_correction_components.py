"""2026-09-25 karşılaştırma farklarını geçici arşivde bileşenlerine ayırır.

Eski davranışlar yalnız bu süreçteki fonksiyon kopyalarında yeniden kurulur.
Kaynak modüller ve üretim defterleri değiştirilmez. Eski sonuçla eşleşme
zorunludur; eşleşmezse bir bileşene kesin atıf yapılmaz.
"""
from __future__ import annotations

import argparse
import copy
import inspect
import json
from pathlib import Path

import pandas as pd

from advisor import costs, history, service, simulation, universe
from advisor.experiments import metrics
from advisor.ledger import atomic_json


GOLD_INTRADAY = "                if cfg['market'] == 'gold':\n                    continue\n"
ZERO_VOLUME = ("                if cfg['market'] == 'bist' and not (r.get('volume', 0) > 0):\n"
               "                    q['tradable'] = False\n")
CUSTODY_CARRY = ("            prior_day = day - timedelta(days=1)\n"
                 "            while not trading_day(prior_day, cfg):\n"
                 "                prior_day -= timedelta(days=1)\n"
                 "            if day > begin:\n"
                 "                last = marks.get(prior_day.isoformat())\n")


def _old_calendar(cfg):
    cfg = copy.deepcopy(cfg)
    cfg['calendar']['years'] = [y for y in cfg['calendar']['years'] if y != '2025']
    for key in ('full_days', 'half_days'):
        cfg['calendar'][key] = [d for d in cfg['calendar'][key] if not d.startswith('2025')]
    return cfg


def _compiled_simulation(*, old_calendar, old_intraday=False, old_zero_volume=False):
    source = inspect.getsource(simulation.simulate)
    for needle, enabled in ((GOLD_INTRADAY, old_intraday), (ZERO_VOLUME, old_zero_volume)):
        if source.count(needle) != 1:
            raise ValueError('Denetim için beklenen simülasyon kodu değişmiş.')
        if enabled:
            source = source.replace(needle, '')
    namespace = dict(simulation.__dict__)
    if old_calendar:
        # Eski sürüm eksik 2025 takvimini reddetmiyor, seans kapısında bekliyordu.
        namespace['require_coverage'] = lambda *args, **kwargs: None
    exec(compile(source, '<memory-correction-audit>', 'exec'), namespace)
    return namespace['simulate']


def _old_custody():
    source = inspect.getsource(costs.accrue)
    if source.count(CUSTODY_CARRY) != 1:
        raise ValueError('Denetim için beklenen saklama kodu değişmiş.')
    namespace = dict(costs.__dict__)
    exec(compile(source.replace(CUSTODY_CARRY, ''), '<memory-custody-audit>', 'exec'), namespace)
    return namespace['accrue']


def _measure(frame, cfg, contract, *, old_calendar=False, old_intraday=False,
             old_custody=False, old_zero_volume=False):
    config = _old_calendar(cfg) if old_calendar else copy.deepcopy(cfg)
    config['research_retrain_sessions'] = 20
    simulate = _compiled_simulation(old_calendar=old_calendar,
                                    old_intraday=old_intraday,
                                    old_zero_volume=old_zero_volume)
    actual = costs.accrue
    if old_custody:
        costs.accrue = _old_custody()
    try:
        run = simulate(frame, config, contract['start'], contract['end'], research=True)
    finally:
        costs.accrue = actual
    series = run['series']
    split = contract['split']
    development_end = max(row['date'] for row in series if row['date'] < split)
    return {
        'development_pct': metrics(series, end=development_end)['return_pct'],
        'holdout_pct': metrics(series, start=split)['return_pct'],
        'fills': len(run['fills']),
        'fees_try': run['fees_try'],
        'pending_custody': run['custody'].get('pending', []),
        'blocked_2025_days': len({row['date'] for row in run['blocks']
                                  if row['date'] < '2026-01-01' and row['reason'] == 'data_block'}),
        'first_buy': next((fill['at'][:10] for fill in run['fills'] if fill['side'] == 'BUY'), None),
    }


def audit(root: Path, names: list[str]) -> dict:
    root = root.resolve()
    current = json.loads((root / 'reports/KARSILASTIRMA-2026-09-25.json').read_text())
    previous = json.loads((root / 'reports/archive/pre-audit-2026-09-25/KARSILASTIRMA-2026-09-25.json').read_text())
    market = service.configuration(root)['market']
    with history.connection(root, market) as con:
        frame = history.load(con, market, current['contract']['end'])
    if market == 'bist':
        watched = universe.members(universe.read(root), service.configuration(root)['start_date'])
        frame['in_live'] = frame.symbol.isin(watched).astype(int)
        frame.attrs['live_symbols'] = sorted(watched)
    data_hash = str(pd.util.hash_pandas_object(frame, index=False).sum())
    if data_hash != current['contract']['data_hash']:
        raise ValueError('Güncel arşiv hash değeri karşılaştırma raporuyla uyuşmuyor.')
    old_frame = frame
    if market == 'bist':
        old_frame = frame[~frame.symbol.isin(('DSTKF', 'TRALT'))].copy()
        old_frame.attrs['live_symbols'] = frame.attrs['live_symbols']
    old_hash = str(pd.util.hash_pandas_object(old_frame, index=False).sum())
    if old_hash != previous['contract']['data_hash']:
        raise ValueError('Eski arşiv hash değeri karşılaştırma raporuyla uyuşmuyor.')

    plans = {row['id']: row['cfg'] for row in current['contract']['plans']}
    now_results = {row['id']: row for row in current['results']}
    old_results = {row['id']: row for row in previous['results']}
    cases = ({'current': {}, 'calendar_old': {'old_calendar': True},
              'intraday_old': {'old_intraday': True},
              'calendar_and_intraday_old': {'old_calendar': True, 'old_intraday': True}}
             if market == 'gold' else
             {'current': {}, 'calendar_old': {'old_calendar': True},
              'history_old': {'old_history': True},
              'calendar_and_history_old': {'old_calendar': True, 'old_history': True},
              'all_old': {'old_calendar': True, 'old_history': True,
                          'old_custody': True, 'old_zero_volume': True}})
    results = {}
    for name in names:
        if name not in plans:
            raise ValueError('Karşılaştırmada yöntem yok: ' + name)
        variants = {}
        for label, switches in cases.items():
            variant_frame = old_frame if switches.get('old_history') else frame
            variants[label] = _measure(variant_frame, plans[name], current['contract'],
                                       old_calendar=switches.get('old_calendar', False),
                                       old_intraday=switches.get('old_intraday', False),
                                       old_custody=switches.get('old_custody', False),
                                       old_zero_volume=switches.get('old_zero_volume', False))
        old_label = 'calendar_and_intraday_old' if market == 'gold' else 'all_old'
        for label, source in (('current', now_results[name]), (old_label, old_results[name])):
            measured = variants[label]
            if (abs(measured['development_pct'] - source['development']['return_pct']) > 1e-8
                    or abs(measured['holdout_pct'] - source['holdout']['return_pct']) > 1e-8
                    or measured['fills'] != source['fills']):
                raise AssertionError(f'{name}/{label} arşiv sonucu yeniden üretilemedi.')
        results[name] = variants
        print(name, {key: (round(row['development_pct'], 6),
                           round(row['holdout_pct'], 6), row['fills'])
                     for key, row in variants.items()}, flush=True)
    return {'market': market, 'period': {'start': current['contract']['start'],
                                         'end': current['contract']['end'],
                                         'split': current['contract']['split']},
            'current_data_hash': data_hash, 'old_data_hash': old_hash,
            'current_code_hash': current['contract']['code_hash'],
            'old_code_hash': previous['contract']['code_hash'],
            'method': 'Bellekte eski korumalar geri alınarak gerçek arşivde aynı karşılaştırma yeniden koşuldu.',
            'old_and_current_results_reproduced': True, 'variants': results,
            'production_data_written': False,
            'limits': ['Bileşenlerin etkisi sıra bağımlıdır; etkileşimler nedeniyle tek bir doğal paylaştırma yok.',
                       'Tarihsel banka kotasyonu ve geçmişte bilinen bütün fiyat sürümleri mevcut değildir.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--methods', nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to((args.root / 'data').resolve()):
        parser.error('Denetim çıktısı gerçek veri dizinine yazılamaz.')
    atomic_json(args.output, audit(args.root, args.methods))
