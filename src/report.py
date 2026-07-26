"""Türkçe markdown raporlar.

Raporun dili ÖLÇÜME göre seçilir, tersi değil. `edge_verdict`'in verdiği hüküm
ne ise cümle o kadar iddialı olur — "doğrulandı" dalı olmadığı için rapor da
hiçbir yerde "doğrulandı" yazamaz.
"""

from __future__ import annotations

from datetime import date

from . import stats, util


def _s(x, ond: int = 2, birim: str = "") -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x):.{ond}f}{birim}"
    except (TypeError, ValueError):
        return str(x)


def _n(x) -> str:
    return "—" if x is None else f"{int(x):,}".replace(",", ".")


def backtest_report(cfg: dict, sonuc: dict) -> str:
    """Faz 2 ölçüm raporu — projenin kapı kararının dayanağı."""
    o = cfg["olcum"]
    L: list[str] = []
    A = L.append

    A(f"# Ölçüm Raporu — {sonuc['tarih']}")
    A("")
    A(f"> {cfg['rapor']['uyari']}")
    A("")

    # ---------------------------------------------------------------- kurulum
    A("## Kurulum")
    A("")
    A(f"- **Evren (ölçüm):** {sonuc['n_ticker']} hisse — `in_measure=1`. "
      f"Kısa geçmişli isimler (ASTOR, EUPWR) ağırlık BELİRLEYEMEZ.")
    A(f"- **Dönem:** {sonuc['ilk_tarih']} … {sonuc['son_tarih']} "
      f"({_n(sonuc['n_bar'])} bar)")
    A(f"- **Ana ufuk:** {sonuc['horizon']} işlem günü, örtüşmeyen pencere, giriş t+1")
    A(f"- **Seçim:** uygun havuzun üst %{sonuc['top_frac']*100:.0f}'i "
      f"(ortalama {_s(sonuc['birlesik'].get('ort_secilen'), 1)} isim / "
      f"{_s(sonuc['birlesik'].get('ort_havuz'), 1)} havuz)")
    A(f"- **Maliyet:** %{sonuc['cost_pct']:.2f} gidiş-dönüş, yalnız seçilen portföye "
      "(EW tabanı ~al-tut olduğu için maliyetsiz — asimetri stratejinin ALEYHİNE)")
    A(f"- **OOS bölme:** {o['oos_split']}")
    A(f"- **Sektör nötralizasyonu:** {'AÇIK' if cfg['faktorler']['sektor_notr'] else 'kapalı'}")
    A("")
    A("**Survivorship bias uyarısı:** evren sabit bir listedir, nokta-zamanlı "
      "BIST-100 üyeliği değil. Bugün likit olan isimleri geçmişe taşımak "
      "sonuçları stratejinin LEHİNE eğer. Düzeltilmiyor; büyüklüğü bilinmiyor.")
    A("")

    # ---------------------------------------------------------------- taban
    t = sonuc["taban_ew_vs_xu100"]
    A("## Taban çizgisi — neden XU100 değil")
    A("")
    A("Eşit-ağırlık uygun evren vs XU100, aynı örtüşmeyen dönemler, **sıfır beceri**:")
    A("")
    A(f"| N | ort | medyan | kazanma | t |")
    A(f"|---|---|---|---|---|")
    A(f"| {t['n']} | {_s(t['ort'], 2, 'pp')} | {_s(t['medyan'], 2, 'pp')} | "
      f"{_s(t['kazanma_pct'], 0, '%')} | {_s(t['t'])} |")
    A("")
    if t["ort"] is not None and t["ort"] > 0:
        A(f"Yani hiçbir seçim yapmadan, sadece eşit ağırlık kullanarak XU100 "
          f"**{_s(t['ort'], 2, 'pp')}/dönem** yeniliyor. \"XU100'e göre alfa\" diye "
          f"raporlanacak her sayı bunu sessizce içerir. **Hüküm bu raporda daima "
          f"EW tabanına göre verilir**; XU100 yalnız iletişim içindir.")
    A("")

    # ---------------------------------------------------------------- kapsama
    b = sonuc["birlesik"]
    atl = b.get("n_atlanan", {})
    A("## Kapsama — sessiz kırpma yok")
    A("")
    A(f"- Ölçülen dönem: **{b['n_donem']}**")
    A(f"- Atlanan: veri yetersiz {atl.get('veri_yok', 0)}, "
      f"uygun isim <2 → {atl.get('uygun_yok', 0)}")
    A(f"- Ortalama uygun havuz: {_s(b.get('ort_havuz'), 1)} / {sonuc['n_ticker']} isim")
    A("")
    A("Uygun isim azaldığında dönem ATILMAZ, portföy küçülür. Aksi halde "
      "kapının daralttığı dönemler (ayı piyasaları) örneklemden tamamen düşer "
      "ve ölçüm yalnız boğa dönemlerinde yapılmış olur.")
    A("")

    # ---------------------------------------------------------------- faktörler
    A("## Faktör bazlı sonuç (ana ufuk, tam dönem)")
    A("")
    A("İki ayrı soru, karıştırılmadan:")
    A("")
    A("- **alfa vs EW** — kapı + seçim birlikte, aynı uygun küme içinde")
    A("- **IC (tüm kesit)** — skor sıralayabiliyor mu? KAPISIZ, tüm geçerli isimler")
    A("")
    A("| Faktör | N | alfa vs **EW** | t | alfa vs XU100 | IC(tüm) | t(IC) | gerekli N | **HÜKÜM** |")
    A("|---|---|---|---|---|---|---|---|---|")
    for ad, r in sonuc["faktorler"].items():
        e, x, ict = r["alfa_ew"], r["alfa_xu100"], r["ic_tum"]
        A(f"| `{ad}` | {e['n']} | {_s(e['ort'], 2, 'pp')} | {_s(e['t'])} | "
          f"{_s(x['ort'], 2, 'pp')} | {_s(ict['ic_ort'], 3)} | {_s(ict['t'])} | "
          f"{_n(e['gerekli_n'])} | **{r['hukum']}** |")
    A(f"| **birleşik** | {b['alfa_ew']['n']} | {_s(b['alfa_ew']['ort'], 2, 'pp')} | "
      f"{_s(b['alfa_ew']['t'])} | {_s(b['alfa_xu100']['ort'], 2, 'pp')} | "
      f"{_s(b['ic_tum']['ic_ort'], 3)} | {_s(b['ic_tum']['t'])} | "
      f"{_n(b['alfa_ew']['gerekli_n'])} | **{b['hukum']}** |")
    A("")
    A(f"`gerekli N` = t=2'ye ulaşmak için gereken **bağımsız dönem** sayısı: "
      f"`(2×sd/|ort|)²`. Yılda ~{sonuc['donem_yil']:.0f} bağımsız dönem üretiliyor "
      f"→ yıl cinsinden bölüp okumak gerekir.")
    A("")

    # ---------------------------------------------------------------- kapı etkisi
    k = sonuc["kapisiz"]
    A("## Kapılar yardım mı ediyor?")
    A("")
    A("| Kurulum | N | alfa vs EW | t | IC(tüm) | **HÜKÜM** |")
    A("|---|---|---|---|---|---|")
    A(f"| kapılı (SMA200 + likidite) | {b['alfa_ew']['n']} | "
      f"{_s(b['alfa_ew']['ort'], 2, 'pp')} | {_s(b['alfa_ew']['t'])} | "
      f"{_s(b['ic_tum']['ic_ort'], 3)} | **{b['hukum']}** |")
    A(f"| kapısız | {k['alfa_ew']['n']} | {_s(k['alfa_ew']['ort'], 2, 'pp')} | "
      f"{_s(k['alfa_ew']['t'])} | {_s(k['ic_tum']['ic_ort'], 3)} | **{k['hukum']}** |")
    A("")
    A("Kapı sıralamadan ÖNCE eler, yani skorun ayırt edeceği aralığı daraltır. "
      "Kapısız satır daha iyiyse kapı bilgi yok ediyor demektir.")
    A("")

    # ---------------------------------------------------------------- IS/OOS
    A("## In-sample / OOS ayrımı (birleşik skor)")
    A("")
    A("| Dilim | N | alfa vs EW | t | IC(tüm) | t(IC) | **HÜKÜM** |")
    A("|---|---|---|---|---|---|---|")
    for ad, r in sonuc["dilimler"].items():
        e = r["alfa_ew"]
        A(f"| {ad} | {e['n']} | {_s(e['ort'], 2, 'pp')} | {_s(e['t'])} | "
          f"{_s(r['ic_tum']['ic_ort'], 3)} | {_s(r['ic_tum']['t'])} | **{r['hukum']}** |")
    A("")

    # ---------------------------------------------------------------- ufuklar
    A("## Ufuk duyarlılığı (birleşik skor)")
    A("")
    A("| H (gün) | N | alfa vs EW | t | kazanma | **HÜKÜM** |")
    A("|---|---|---|---|---|---|")
    for h, r in sonuc["ufuklar"].items():
        e = r["alfa_ew"]
        isaret = " ⚠ kenarsız kabul edilen ufuk" if h in o["kenarsiz_ufuklar"] else ""
        A(f"| {h}{isaret} | {e['n']} | {_s(e['ort'], 2, 'pp')} | {_s(e['t'])} | "
          f"{_s(e['kazanma_pct'], 0, '%')} | **{r['hukum']}** |")
    A("")

    # ---------------------------------------------------------------- maliyet
    A("## Maliyet duyarlılığı (birleşik skor, ana ufuk)")
    A("")
    A("| Gidiş-dönüş maliyet | alfa vs EW | t | **HÜKÜM** |")
    A("|---|---|---|---|")
    for c, r in sonuc["maliyetler"].items():
        e = r["alfa_ew"]
        A(f"| %{c:.2f} | {_s(e['ort'], 2, 'pp')} | {_s(e['t'])} | **{r['hukum']}** |")
    A("")

    # ---------------------------------------------------------------- kapı
    A("## Kapı kararı")
    A("")
    A(f"**Kural:** OOS'ta hiçbir faktör EW tabanına göre `zayıf kanıt` seviyesine "
      f"ulaşmazsa Faz 3-6'ya geçilmez.")
    A("")
    gecen = sonuc["kapi"]["gecen"]
    ters = sonuc["kapi"].get("ters", [])
    ic_gecen = sonuc["kapi"]["ic_gecen"]
    A("`edge_verdict` bir **büyüklük** hükmüdür (|fark|'a bakar), yön hükmü değil. "
      "Kapı **pozitif** kanıt ister; negatif kanıt ayrı ve değerli bir bulgudur.")
    A("")
    if gecen:
        A(f"✅ **Kapı AÇIK.** OOS'ta POZİTİF `zayıf kanıt` üreten faktör(ler): "
          f"{', '.join(f'`{x}`' for x in gecen)}")
    else:
        A("🛑 **Kapı KAPALI.** OOS'ta hiçbir faktör EW tabanına göre POZİTİF "
          "`zayıf kanıt` seviyesine ulaşmadı.")
    A("")
    if ters:
        A(f"⚠️ **Ters yönde kanıt:** {', '.join(f'`{x}`' for x in ters)} — bu "
          "faktörlerin seçtiği isimler tabanın ALTINDA kalıyor. Bu bir "
          "başarısızlık değil, bir BULGUDUR: ilgili faktör kaldırılmalı ya da "
          "işareti ölçüme göre yeniden ele alınmalı. Ters sinyali \"kanıt\" "
          "sayıp kapıyı açmak, sistemin kendini kandırmasının en kısa yoludur.")
        A("")
    A("**İkincil okuma — sıralama kalitesi (IC).** Alfa ile IC aynı şeyi ölçmez: "
      "alfa dar bir seçimin getirisidir ve maliyet + yoğunlaşma gürültüsü taşır, "
      "IC ise tüm kesitin sıralanabilirliğidir.")
    A("")
    if ic_gecen:
        A(f"OOS'ta t(IC) ≥ 2 olan: {', '.join(f'`{x}`' for x in ic_gecen)} — "
          "yani sıralama sinyali var ama seçim getiriye çevrilemiyor. Bu, "
          "\"faktör çalışmıyor\"dan FARKLI bir teşhistir; önce seçim genişliği, "
          "maliyet ve kapı tasarımı gözden geçirilmeli.")
    else:
        A("OOS'ta t(IC) ≥ 2 olan faktör de YOK. Yani sorun yalnız seçimin dar "
          "olması değil — skor bu evrende kesiti sıralayamıyor.")
    A("")
    A(f"> {stats.bonferroni_note(sonuc['n_test'])}")
    A("")
    A("---")
    A("")
    A("### Bu raporun okunma kuralları")
    A("")
    A("- **Hüküm daima EW tabanına göre.** XU100 sütunu bilgi içindir, karar için değil.")
    A("- **Zayıf N büyük farkı ezer.** `ölçüm yetersiz` gördüğün satırdaki büyük "
      "yüzde bir bulgu değildir.")
    A("- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde \"doğrulandı\" hükmü YOKTUR.")
    A("- **Tek tek \"en iyi\" satıra bakma** — çoklu test uyarısına bak.")
    return "\n".join(L)


def write(cfg: dict, ad: str, icerik: str) -> str:
    """Raporu `reports/` altına yazar ve yolu döner."""
    p = util.ensure_parent(f"{cfg['paths']['reports_dir']}/{ad}")
    p.write_text(icerik + "\n", encoding="utf-8")
    return str(p)


def bugun() -> str:
    return date.today().isoformat()
