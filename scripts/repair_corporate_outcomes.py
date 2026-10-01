"""Varsayılan salt-okur düzeltme planı; --apply-plan açık ve sürümlü uygulama."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from advisor.ledger import atomic_json
from src import corporate_repair, util

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True)
    p.add_argument('--actions',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--apply-plan',type=Path)
    p.add_argument('--config',type=Path,default=Path('config.yaml'))
    args=p.parse_args()
    if args.output.resolve()==args.database.resolve():p.error('Rapor veritabanının üzerine yazılamaz.')
    if args.output.exists():p.error('Kanıt dosyası mevcut; farklı çıktı yolu seçin.')
    if args.apply_plan:
        plan=json.loads(args.apply_plan.read_text())
        # Plan kalıcı olarak mevcut olmadan SQL değiştirilemez.
        with sqlite3.connect(args.database) as con:
            con.row_factory=sqlite3.Row
            result=corporate_repair.apply(con,plan)
    else:
        if not args.actions:p.error('--actions gerekli.')
        payload=json.loads(args.actions.read_text())
        if isinstance(payload,dict):
            if any(not record.get('ok') for record in payload.values()):p.error('Doğrulanmamış kurumsal kaynak var.')
            payload=[a for record in payload.values() for a in record['actions']]
        con=sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True)
        con.row_factory=sqlite3.Row
        try:result=corporate_repair.plan(util.load_config(args.config),con,payload)
        finally:con.close()
    atomic_json(args.output,result)
    print(json.dumps({'output':str(args.output),'changes':len(result.get('changes',[])) if not args.apply_plan else result['changed']},ensure_ascii=False))
