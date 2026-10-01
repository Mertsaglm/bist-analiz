import json,shutil,subprocess,sys
from pathlib import Path
root=Path.cwd();out=Path('/tmp/bist-fix-20260930');work=out/'mutation'
for name in ['src','advisor','scripts','tests','schema']:
 if (root/name).exists():shutil.copytree(root/name,work/name,ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
for name in ['config.yaml','holidays_tr.yaml','universe.yaml','pyproject.toml']:
 shutil.copy2(root/name,work/name)
files=['src/otonom.py','src/resolver.py','src/sources/kap.py','advisor/calendar.py','scripts/audit_production.py','scripts/refresh_market_history.py']
original={n:(work/n).read_text() for n in files}
cases=[]
s=original['src/otonom.py'];start=s.index('    # D-01:');end=s.index('    # 2b)',start)
cases.append(('daily_corporate','src/otonom.py',s[:start]+s[end:],'test_daily_fetches_corporate_before_decision_and_stops_on_source_failure'))
for tag,file,test in [('late_corporate','src/resolver.py','test_corporate_after_closed_trade_cannot_erase_its_result'),('kap_clip','src/sources/kap.py','test_expected_calendar_splits_full_window_and_requires_all_slices'),('audit_accounts','scripts/audit_production.py','test_auditor_finds_every_account_and_handles_fee_debt')]:
 cases.append((tag,file,subprocess.check_output(['git','show','HEAD:'+file],text=True),test))
s=original['advisor/calendar.py'];s=s[:s.index('def last_closed_session')]+"def last_closed_session(now, cfg):\n    return now.astimezone(IST).date()\n"
cases.append(('midnight','advisor/calendar.py',s,'test_closing_date_is_a_session_not_midnight'))
s=original['scripts/refresh_market_history.py'].replace('prices.daily(legacy, con, tickers=before)','pass  # mutation: no catch-up')
cases.append(('catchup','scripts/refresh_market_history.py',s,'test_refresh_catches_missing_close_and_skips_after_recovery'))
results=[]
for tag,file,mutated,test in cases:
 (work/file).write_text(mutated)
 p=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_production_repairs.py::'+test],cwd=work,text=True,capture_output=True)
 (out/('mutation-'+tag+'.log')).write_text(p.stdout+p.stderr)
 results.append({'case':tag,'exit_code':p.returncode,'failed_as_expected':p.returncode==1})
 (work/file).write_text(original[file])
 print(tag,p.returncode,flush=True)
(out/'mutation-results.json').write_text(json.dumps(results,indent=2))
assert all(r['failed_as_expected'] for r in results)
