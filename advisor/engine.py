"""Canlı koşu ve yeniden üretimin tek karar/uygulama sınırı."""
from . import marketdata, policy
from .calendar import IST
from .ledger import digest


def run(ledger, rows, forecasts, model, cfg, quotes, now, event_note=None, book='strategy'):
    account=ledger.account(book);local_day=now.astimezone(IST).date().isoformat()
    decisions=[]
    for row in rows:
        symbol=row['symbol']
        block=marketdata.usable(quotes.get(symbol),cfg,now,cfg.get('holidays',()),allow_wide_spread=symbol in account['positions'])
        if cfg.get('execution_phase') == 'valuation':
            block = marketdata.price_problem(quotes.get(symbol), cfg, now)
        block=cfg.get('blocked_symbols',{}).get(symbol,block)
        d=policy.decision(row,forecasts.get(symbol),model,cfg,quotes.get(symbol),account['positions'].get(symbol),block,now)
        if event_note:d['event_note']=event_note
        if cfg['market']=='gold' and d['action']=='TUT':
            last_buy=max((f['at'] for f in account['fills'] if f['symbol']==symbol and f['side']=='BUY'),default='')
            if last_buy[:7]<local_day[:7]:
                topup=policy.decision(row,forecasts.get(symbol),model,cfg,quotes.get(symbol),None,block,now)
                if topup['action']=='AL':d={**topup,'monthly_topup':True}
        if d['action']=='AL' and 'allowed_entry_symbols' in cfg and symbol not in cfg['allowed_entry_symbols']:
            d.update(action='BEKLE',code='outside_universe',reasons=['İzleme evreni dışında; yalnız mevcut pozisyon izlenir.'])
        if d['action'] == 'AL' and cfg.get('execution_phase', 'entry') != 'entry':
            d.update(action='BEKLE', code='entry_window_closed', reasons=['Yeni alım saati bitti; fiyat ve mevcut pozisyonlar izleniyor.'])
        if cfg.get('execution_phase') == 'valuation' and d['action'] in ('AL', 'SAT'):
            d.update(action='BEKLE', code='valuation_only', reasons=['Kapanış değerlemesi; bu saatte sanal dolum üretilmez.'])
        if d['action'] == 'AL' and not marketdata.entry_ready(ledger, cfg, quotes.get(symbol), symbol, now, book):
            d.update(action='BEKLE', code='awaiting_next_quote', reasons=['Alım adayı kaydedildi; sonraki taze kotasyonda koşullar yeniden sınanacak.'])
        d['key']='decision:'+digest({'day':local_day,'data':d,'quote':quotes.get(symbol)})
        decisions.append(d)
    fills=policy.execute(ledger,cfg,decisions,quotes,now,book=book)
    return decisions,fills
