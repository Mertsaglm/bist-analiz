"""Mühürlü V2 defterinden karar etkinliği ve gerçekleşmeyen alım ölçümü."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from advisor import calendar, history
from advisor.decision_activity import measure
from advisor.accounts import state_path
from advisor.ledger import Ledger, cents
from advisor.service import configuration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--through', required=True)
    parser.add_argument('--budget-try', type=Decimal, default=Decimal('1000'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.output.resolve().is_relative_to(root / 'data'):
        parser.error('Rapor kaynak veri dizinine yazılamaz.')
    if not args.budget_try.is_finite() or cents(args.budget_try) < 1 or args.through < args.start:
        parser.error('Tarih aralığı ve pozitif TL bütçesi doğrulanmalı.')
    cfg = configuration(root)
    cfg['calendar'] = calendar.load(root)
    ledger_path = state_path(root, cfg) / 'events.jsonl'
    if not ledger_path.is_file():
        parser.error('V2 olay defteri bulunamadı.')
    ledger = Ledger(ledger_path)
    corporate_days = defaultdict(set)
    if cfg['market'] == 'bist':
        with history.connection(root, 'bist') as con:
            for symbol, day in con.execute('SELECT ticker,date FROM corporate_actions WHERE date BETWEEN ? AND ?',
                                           (args.start, args.through)):
                corporate_days[symbol].add(date.fromisoformat(day))
    result = measure(ledger, cfg, start=args.start, through=args.through,
                     budget=cents(args.budget_try), corporate_days=corporate_days)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
