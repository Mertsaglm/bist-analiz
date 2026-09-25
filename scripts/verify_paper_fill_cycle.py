"""2026-09-25 sanal alım ve stop/hedef satışını geçici arşivde sınar."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from advisor import history, learning, service
from advisor.accounts import state_path
from advisor.calendar import IST
from advisor.ledger import Ledger, atomic_json


def tree_sha256(directory: Path) -> str:
    digest = hashlib.sha256()
    if directory.exists():
        for path in sorted(item for item in directory.rglob('*') if item.is_file()):
            digest.update(str(path.relative_to(directory)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def run(root: Path) -> dict:
    root = root.resolve()
    now = datetime(2026, 9, 25, 10, 30, tzinfo=IST)
    source_hash = hashlib.sha256((root / 'data/bist.sql').read_bytes()).hexdigest()
    state_hash = tree_sha256(root / 'data/advisor')
    with tempfile.TemporaryDirectory(prefix='advisor-paper-fill-audit-') as temporary:
        trial = Path(temporary) / 'stop'
        trial.mkdir()
        (trial / 'advisor').mkdir()
        for name in ('config.json', 'universe-history.json'):
            shutil.copy2(root / 'advisor' / name, trial / 'advisor' / name)
        shutil.copy2(root / 'holidays_tr.yaml', trial / 'holidays_tr.yaml')

        database = trial / 'archive.db'
        with history.connection(root, 'bist') as source:
            with sqlite3.connect(database) as destination:
                source.backup(destination)
        with sqlite3.connect(database) as con:
            latest = con.execute('SELECT max(date) FROM bars_daily').fetchone()[0]
            if latest != '2026-09-22':
                raise ValueError('Denetim arşivi değişti; 2026-09-22 kesimi gerekli: ' + str(latest))
            bar = con.execute(
                "SELECT ticker,o,h,l,c,v,c_tr,turnover_try FROM bars_daily "
                "WHERE ticker='TUPRS' AND date='2026-09-22'").fetchone()
            if bar is None:
                raise ValueError('Kontrollü TUPRS barı için 2026-09-22 referansı yok.')
            con.execute(
                'INSERT INTO bars_daily(ticker,date,o,h,l,c,v,c_tr,turnover_try,source,ingested_utc) '
                'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (bar[0], '2026-09-24', *bar[1:], 'controlled_fixture', now.isoformat()))
            con.commit()

        actual_train = learning.train

        def controlled_train(frame, cfg, asof):
            if cfg.get('strategy_kind') == 'sma50':
                return actual_train(frame, cfg, asof)
            features = learning.features(frame, cfg['horizon_sessions'])
            names = cfg['learning'].get('features') or (
                learning.ADAPTIVE_FEATURES if cfg['learning'].get('feature_set') == 'adaptive_v1'
                else learning.FEATURES)
            model = {'ready': True, 'id': 'controlled-forecast-' + str(cfg['horizon_sessions']),
                     'approved': False, 'asof': asof, 'horizon_sessions': cfg['horizon_sessions'],
                     'features': list(names), 'weights': [0] * len(names),
                     'mean': [0] * len(names), 'scale': [1] * len(names),
                     'intercept': 50.0, 'evaluation': {'periods': 0},
                     'limitations': ['Kontrollü test tahmini; yatırım kanıtı değildir.']}
            return model, features

        def quote(at, bid=397.0, ask=397.2):
            return {'symbol': 'TUPRS', 'bid': bid, 'ask': ask,
                    'reference_price': bid, 'quoted_at': at.isoformat(),
                    'observed_at': at.isoformat(), 'source': 'controlled_fixture',
                    'kind': 'controlled_test', 'tradable': True}

        learning.train = controlled_train
        try:
            first = service.cycle(trial, database=database, now=now,
                                  quotes={'TUPRS': quote(now)}, offline=True)
            later = now + timedelta(minutes=5)
            second = service.cycle(trial, database=database, now=later,
                                   quotes={'TUPRS': quote(later)}, offline=True)
            third = service.cycle(trial, database=database, now=later + timedelta(minutes=1),
                                  quotes={'TUPRS': quote(later)}, offline=True)
            bought_ledger = Ledger(state_path(trial, service.configuration(trial)) / 'events.jsonl')
            position = bought_ledger.account()['positions']['TUPRS']
            target_trial = Path(temporary) / 'target'
            shutil.copytree(trial, target_trial)
            exit_at = later + timedelta(minutes=5)
            stop_bid = float(position['stop']) * 0.99
            target_bid = float(position['target']) * 1.01
            exit_quotes = {
                'stop': quote(exit_at, stop_bid, stop_bid * 1.001),
                'target': quote(exit_at, target_bid, target_bid * 1.001),
            }
            exits = {}
            for reason, branch in (('stop', trial), ('target', target_trial)):
                branch_database = branch / 'archive.db'
                sold = service.cycle(branch, database=branch_database, now=exit_at,
                                     quotes={'TUPRS': exit_quotes[reason]}, offline=True)
                repeated_sell = service.cycle(
                    branch, database=branch_database, now=exit_at + timedelta(minutes=1),
                    quotes={'TUPRS': exit_quotes[reason]}, offline=True)
                exits[reason] = (sold, repeated_sell, Ledger(
                    state_path(branch, service.configuration(branch)) / 'events.jsonl'))
        finally:
            learning.train = actual_train

        def decision(snapshot):
            return next(d for d in snapshot['decisions'] if d['symbol'] == 'TUPRS')

        before, opened, repeated = map(decision, (first, second, third))
        fills = second['strategy']['fills']
        if len(fills) != 1:
            raise AssertionError('İkinci taze kotasyonda tek strateji dolumu bekleniyordu.')
        fill = fills[0]
        ledger = bought_ledger
        account = ledger.account()
        conservation = (account['cash_cents'] + fill['notional_cents'] + fill['fee_cents']
                        == account['contributed_cents'])
        checks = {
            'first_quote_waited': (before['action'], before['code']) == ('BEKLE', 'awaiting_next_quote')
                                  and not first['strategy']['fills'],
            'second_quote_bought': (opened['action'], opened['code']) == ('AL', 'cost_adjusted_opportunity')
                                   and fill['side'] == 'BUY' and fill['decision_key'] == opened['key'],
            'account_balanced': conservation and account['cash_cents'] > 0
                                and account['positions']['TUPRS']['quantity'] == int(fill['quantity']),
            'repeat_idempotent': len(third['strategy']['fills']) == 1,
            'valuation_complete': second['strategy']['valuation_complete'],
            'no_cycle_errors': not first['health']['errors'] and not second['health']['errors']
                               and not third['health']['errors'],
        }
        if not all(checks.values()):
            raise AssertionError('Sanal dolum zinciri doğrulanamadı: ' + str(checks))
        strategy_intents = sum(e['kind'] == 'entry_intent' and e['data']['book'] == 'strategy'
                               for e in ledger.events)
        if strategy_intents != 1:
            raise AssertionError('Strateji için tam bir giriş niyeti bekleniyordu.')
        exit_reports = {}
        for reason, (sold, repeated_sell, exit_ledger) in exits.items():
            sale_decision = decision(sold)
            sale_account = exit_ledger.account()
            sale_fills = sale_account['fills']
            sale = sale_fills[-1]
            sale_checks = {
                'decision_and_fill': sale_decision['action'] == 'SAT'
                                     and sale_decision['code'] == reason
                                     and sale['side'] == 'SELL'
                                     and sale['reason'] == reason
                                     and sale['decision_key'] == sale_decision['key'],
                'full_position_closed': len(sale_fills) == 2
                                        and sale['quantity'] == fill['quantity']
                                        and not sale_account['positions'],
                'cash_and_realized_balanced': (
                    sale_account['cash_cents'] == account['contributed_cents']
                    - fill['notional_cents'] - fill['fee_cents']
                    + sale['notional_cents'] - sale['fee_cents']
                    == account['contributed_cents'] + sale_account['realized_cents']),
                'equity_equals_cash': sold['strategy']['valuation_complete']
                                      and sold['strategy']['equity_try']
                                      == sale_account['cash_cents'] / 100,
                'repeat_does_not_refill': len(repeated_sell['strategy']['fills']) == 2,
                'roundtrip_counted': sold['feedback']['roundtrips'] == 1,
                'no_cycle_errors': not sold['health']['errors']
                                   and not repeated_sell['health']['errors'],
            }
            if not all(sale_checks.values()):
                raise AssertionError('Sanal satış zinciri doğrulanamadı: '
                                     + reason + ' ' + str(sale_checks))
            exit_reports[reason] = {
                'trigger_level': position[reason],
                'quote': exit_quotes[reason],
                'decision': {'action': sale_decision['action'], 'code': sale_decision['code']},
                'fill': {k: sale[k] for k in ('side', 'symbol', 'quantity', 'price',
                                             'notional_cents', 'fee_cents', 'at', 'decision_key')},
                'account': {'cash_cents': sale_account['cash_cents'],
                            'realized_cents': sale_account['realized_cents'],
                            'positions': len(sale_account['positions']),
                            'equity_try': sold['strategy']['equity_try'],
                            'roundtrips': sold['feedback']['roundtrips']},
                'checks': sale_checks,
                'ledger_hash': exit_ledger.root_hash,
            }
        if (source_hash != hashlib.sha256((root / 'data/bist.sql').read_bytes()).hexdigest()
                or state_hash != tree_sha256(root / 'data/advisor')):
            raise AssertionError('Üretim SQL arşivi veya advisor defteri değişti.')
        return {
            'mode': 'isolated_controlled_paper_cycle', 'market': 'bist',
            'archive_source_sha256': source_hash, 'production_state_sha256': state_hash,
            'archive_through': latest, 'injected_bar': {'symbol': 'TUPRS', 'date': '2026-09-24',
                                                       'copied_from': '2026-09-22',
                                                       'only_in_temporary_database': True},
            'model': {'kind': 'controlled_constant_forecast', 'forecast_pct': 50.0,
                      'approved': False, 'only_in_temporary_state': True},
            'quotes': {'first': quote(now), 'second': quote(later)},
            'decisions': {'first': {'action': before['action'], 'code': before['code']},
                          'second': {'action': opened['action'], 'code': opened['code']},
                          'third': {'action': repeated['action'], 'code': repeated['code']}},
            'strategy_fill': {k: fill[k] for k in ('side', 'symbol', 'quantity', 'price',
                                                  'notional_cents', 'fee_cents', 'at', 'decision_key')},
            'strategy_account': {'contributed_cents': account['contributed_cents'],
                                 'cash_cents': account['cash_cents'],
                                 'position_quantity': str(account['positions']['TUPRS']['quantity']),
                                 'equity_try': second['strategy']['equity_try']},
            'strategy_entry_intents': strategy_intents, 'checks': checks,
            'exit_branches': exit_reports,
            'candidate_count': len(second.get('candidates', [])),
            'no_external_requests': True, 'production_state_written': False,
            'production_archive_and_state_unchanged': True,
            'ledger_hash': ledger.root_hash,
            'limitation': 'Kontrollü bar, kotasyon ve sabit tahmin; gerçek banka veya piyasa dolumu değildir.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to((args.root / 'data').resolve()):
        parser.error('Denetim makbuzu gerçek veri dizinine yazılamaz.')
    result = run(args.root)
    atomic_json(args.output, result)
    print(json.dumps({'report': str(args.output), 'buy_checks': result['checks'],
                      'exit_checks': {reason: branch['checks']
                                      for reason, branch in result['exit_branches'].items()}},
                     ensure_ascii=False))
