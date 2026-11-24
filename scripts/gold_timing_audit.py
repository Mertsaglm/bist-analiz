"""İş Bankası giriş gözlemlerinde aynı gün zamanlama ve T0 kanıtı."""
import argparse
from datetime import datetime, time
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from advisor import calendar, marketdata, portfolio_candidates as portfolio
from advisor.ledger import Ledger, canonical


def compare(source, cfg, start, end, work):
    grouped = {}
    for event in source.events:
        if event['kind'] != 'quote_snapshot':
            continue
        at = datetime.fromisoformat(event['at']).astimezone(calendar.IST)
        day = at.date().isoformat()
        if not start <= day <= end or calendar.phase(at, cfg) != 'entry':
            continue
        grouped.setdefault(day, [])
        quote = event['data']['quotes'].get('GRAM')
        if quote and quote.get('kind') != 'historical_assumption' and not marketdata.price_problem(quote, cfg, at):
            grouped[day].append((at, quote))
    results = []
    for day, observations in sorted(grouped.items()):
        if not observations:
            results.append({'day': day, 'valid_quotes': 0, 'at_core_cap': 0, 'fills': {}})
            continue
        observations.sort(key=lambda item: item[0])
        fills = {}
        core_cfg = portfolio.core_quote_config(cfg)
        at_cap = sum(not marketdata.usable(q, core_cfg, at) for at, q in observations)
        for arm in ('first', 'wait-until-1530'):
            trial = Ledger(work / day / arm)
            trial.add('contribution', 'cash', observations[0][0].isoformat(), book='core',
                      period=day, amount_cents=100_000)
            for at, quote in observations:
                cap = 2.75 if arm == 'wait-until-1530' and at.time() < time(15, 30) else 4.
                arm_cfg = {**cfg, 'require_next_quote': True, 'execution_phase': 'entry', 'max_spread_pct': cap}
                action = portfolio._trade(trial, arm_cfg, {'GRAM': quote}, at, 'core', 'GRAM', 'BUY', 1000)
                if action['status'] == 'doldu':
                    acc = trial.account('core')
                    fills[arm] = {'at': at.isoformat(), 'ask': quote['ask'],
                                  'cash_try': acc['cash_cents'] / 100,
                                  'grams': action['quantity'], 'fee_try': action['fee_try']}
                    break
        results.append({'day': day, 'valid_quotes': len(observations), 'at_core_cap': at_cap, 'fills': fills})
    return {'source_event_hash': source.root_hash, 'start': start, 'end': end, 'days': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--start', default='2026-09-25')
    parser.add_argument('--end', default='2026-11-24')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.ledger.is_file():
        parser.error('Kaynak defter dosyası gerekli.')
    cfg = json.loads(args.config.read_text())
    cfg['calendar'] = calendar.load(args.config.resolve().parents[1])
    with TemporaryDirectory(prefix='gold-timing-audit-') as tmp:
        result = compare(Ledger(args.ledger), cfg, args.start, args.end, Path(tmp))
    with args.output.open('x', encoding='utf-8') as out:
        out.write(canonical(result) + '\n')


if __name__ == '__main__':
    main()
