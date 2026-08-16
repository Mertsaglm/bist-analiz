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
    # ⚠ İFŞA: düşürülen gözlem sayısı SESSİZ kalamaz. Bir eleme raporda
    # görünmüyorsa, o eleme bir sonraki okuyucu için görünmez bir varsayımdır.
    A(f"- **Kirli gözlem düşürüldü: {atl.get('kirli_gozlem', 0)}** — plan "
      "penceresine düzeltilmemiş bir kurumsal işlem barı düşen (ticker, dönem) "
      "çiftleri. Bunlar getiri değil, veri hatasıdır (bkz. "
      "`backtest.bozuk_bar_mask`); ismin TAMAMI değil yalnız o gözlem düşer.")
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


def diagnose_report(cfg: dict, t: dict, h: dict) -> str:
    """Teşhis raporu — hüküm vermez, mekanizma adlandırır."""
    L: list[str] = []
    A = L.append
    r = t["referans"]
    e = t["enstruman"]

    A(f"# Teşhis Raporu — {bugun()}")
    A("")
    A("> ⚠ **Bu bir revizyon turu DEĞİLDİR.** Burada strateji seçilmez; enstrüman "
      "doğrulanır ve kayıp bileşenlerine ayrılır. Hiçbir varyant \"kazanan\" ilan "
      "edilmez; her kol ortak referanstan TEK TEK saptırılır, kombinasyon aranmaz.")
    A("")
    A(f"**Referans kurulum:** {r['ayar']} → alfa vs EW "
      f"**{_s(r['alfa']['ort'], 2, 'pp')}** (t={_s(r['alfa']['t'])}, N={r['alfa']['n']})")
    A("")

    # ------------------------------------------------- 1) enstrüman
    A("## 1. Enstrüman doğrulaması — IC>0 iken alfa<0 nasıl olur?")
    A("")
    A("İki IC aynı şeyi ölçmüyor. Ayrışmanın kaynağı bu tabloda:")
    A("")
    A("| Ölçüm | popülasyon | IC ort | t | yorum |")
    A("|---|---|---|---|---|")
    A(f"| `ic_tum` | KAPISIZ tüm kesit (~{r['ic_tum']['n_donem']} dönem × tüm isimler) | "
      f"{_s(e['ic_tum']['ic_ort'], 3)} | {_s(e['ic_tum']['t'])} | skor sıralayabiliyor mu |")
    A(f"| `ic_uygun` | KAPILI havuz içi (ort. {_s(e['ort_havuz'], 1)} isim) | "
      f"{_s(e['ic_uygun']['ic_ort'], 3)} | {_s(e['ic_uygun']['t'])} | kapıdan sonra kalan bilgi |")
    A("")
    A(f"**Seçim yönü tutarlılığı:** seçilenlerin ortalama skoru havuz ortalamasından "
      f"yüksek olan dönem oranı = **%{e['secim_yonu_dogru_oran']*100:.0f}** "
      f"({e['secim_yonu_n']} dönem). %100'den sapma sıralamanın ters uygulandığını gösterir.")
    A("")
    A(f"### Tanı: `{h['tani']}`")
    A("")
    A(h["aciklama"])
    A("")

    # ------------------------------------------------- 2) atıf
    A("## 2. Atıf — kayıp hangi kolda?")
    A("")
    A("Her satır referanstan **tek bir** sapmadır. `Δ` = o kolun tek başına "
      "getirdiği alfa değişimi (pp).")
    A("")
    A("| Kol | N | alfa vs EW | **Δ** | t | IC(tüm) | IC(uygun) |")
    A("|---|---|---|---|---|---|---|")
    A(f"| _referans_ | {r['alfa']['n']} | {_s(r['alfa']['ort'], 2, 'pp')} | — | "
      f"{_s(r['alfa']['t'])} | {_s(e['ic_tum']['ic_ort'], 3)} | "
      f"{_s(e['ic_uygun']['ic_ort'], 3)} |")
    for a in t["atif"]:
        A(f"| {a['kol']} | {a['n']} | {_s(a['alfa'], 2, 'pp')} | "
          f"**{_s(a['delta'], 2, 'pp')}** | {_s(a['t'])} | "
          f"{_s(a['ic_tum'], 3)} | {_s(a['ic_uygun'], 3)} |")
    A("")
    if h.get("baskin_kol"):
        b = h["baskin_kol"]
        A(f"**Baskın kol:** `{b['kol']}` → tek başına {_s(b['delta'], 2, 'pp')} "
          f"iyileşme getiriyor.")
    A("")

    # ------------------------------------------------- 3) IC × ufuk
    A("## 3. Sıralama bilgisi hangi ufukta yaşıyor? (kapısız, tüm kesit)")
    A("")
    A("| H (gün) | N | IC ort | t(IC) | alfa vs EW | t |")
    A("|---|---|---|---|---|---|")
    for hh, v in t["ic_ufuk"].items():
        A(f"| {hh} | {v['n']} | {_s(v['ic']['ic_ort'], 3)} | {_s(v['ic']['t'])} | "
          f"{_s(v['alfa']['ort'], 2, 'pp')} | {_s(v['alfa']['t'])} |")
    A("")

    # ------------------------------------------------- 4) faktör × IC
    A("## 4. Faktör bazlı sıralama bilgisi (kapısız)")
    A("")
    A("| Faktör | IC tam | t | IC OOS | t | alfa tam | alfa OOS |")
    A("|---|---|---|---|---|---|---|")
    for ad, v in t["faktor_ic"].items():
        A(f"| `{ad}` | {_s(v['tam']['ic_ort'], 3)} | {_s(v['tam']['t'])} | "
          f"{_s(v['oos']['ic_ort'], 3)} | {_s(v['oos']['t'])} | "
          f"{_s(v['alfa_tam']['ort'], 2, 'pp')} | {_s(v['alfa_oos']['ort'], 2, 'pp')} |")
    A("")
    A(f"> {stats.bonferroni_note(t['n_test'])} — teşhis adımı olduğu için burada "
      "hüküm verilmiyor; bu tablolar bir sonraki deneyi TASARLAMAK içindir.")
    return "\n".join(L)


def revizyon_report(cfg: dict, r: dict) -> str:
    """Ön kayıtlı revizyon turu raporu. Karar MEKANİK, ön kayıttaki kurala göre."""
    L: list[str] = []
    A = L.append
    y, ref, k = r["yeni"], r["referans"], r["karar"]

    A(f"# Ön Kayıtlı Revizyon Turu #1 — {bugun()}")
    A("")
    A(f"> Ön kayıt: `docs/on-kayit-revizyon-01.md`")
    A(f"> sha256 (koşudan **önce** mühürlendi): `{r['on_kayit_sha'][:32]}…`")
    A("")
    A(f"**Karar kuralı (sonucu görmeden yazıldı):** {k['kural']}")
    A("")
    a = r["ayar"]
    A(f"**Konfigürasyon:** H={a['ufuk']} · SMA200 kapısı **KAPALI** "
      f"(likidite+veri kapıları açık) · üst %{a['top_frac']*100:.0f} · "
      f"%{a['maliyet']:.2f} maliyet · {a['evren']} isim · OOS {a['oos_split']}")
    A("")

    A("## Sonuç")
    A("")
    A("| Kurulum | dilim | N | alfa vs EW | t | IC(tüm) | t(IC) | hüküm |")
    A("|---|---|---|---|---|---|---|---|")
    for ad, d, s in (("referans", "tam", ref["tam"]), ("referans", "OOS", ref["oos"]),
                     ("**yeni**", "tam", y["tam"]), ("**yeni**", "in-sample", y["in_sample"]),
                     ("**yeni**", "**OOS**", y["oos"])):
        e = s["alfa_ew"]
        A(f"| {ad} | {d} | {e['n']} | {_s(e['ort'], 2, 'pp')} | {_s(e['t'])} | "
          f"{_s(s['ic_tum']['ic_ort'], 3)} | {_s(s['ic_tum']['t'])} | {s['hukum']} |")
    A("")

    A("## Tek-kol OOS katkıları (yorumlanabilirlik — karar VERMEZ)")
    A("")
    A("İki değişiklik birlikte test edildi çünkü bağımsız değiller "
      "(H=42 aynı zamanda `high52_prox`'un ağırlığını sıfırdan çıkarıyor). "
      "Hangisinin ne kadar getirdiği yine de ayrıştırılabilir:")
    A("")
    A("| Kol | N | alfa vs EW | t | IC(uygun) |")
    A("|---|---|---|---|---|")
    for ad, s in r["kollar"].items():
        e = s["alfa_ew"]
        A(f"| {ad} | {e['n']} | {_s(e['ort'], 2, 'pp')} | {_s(e['t'])} | "
          f"{_s(s['ic']['ic_ort'], 3)} |")
    A(f"| **ikisi birlikte (ön kayıtlı)** | {y['oos']['alfa_ew']['n']} | "
      f"**{_s(y['oos']['alfa_ew']['ort'], 2, 'pp')}** | "
      f"{_s(y['oos']['alfa_ew']['t'])} | {_s(y['oos']['ic']['ic_ort'], 3)} |")
    A("")

    A("## Faktör bazlı OOS (yeni konfigürasyon)")
    A("")
    A("| Faktör | N | alfa vs EW | t | IC(tüm) | t(IC) | hüküm |")
    A("|---|---|---|---|---|---|---|")
    for ad, s in r["faktorler"].items():
        e = s["alfa_ew"]
        A(f"| `{ad}` | {e['n']} | {_s(e['ort'], 2, 'pp')} | {_s(e['t'])} | "
          f"{_s(s['ic_tum']['ic_ort'], 3)} | {_s(s['ic_tum']['t'])} | {s['hukum']} |")
    A("")

    A("## KARAR")
    A("")
    o = k["olculen"]
    A(f"Ölçülen (OOS): N={o['N']}, Δ={_s(o['delta'], 2, 'pp')}, t={_s(o['t'])} "
      f"→ `{k['hukum']}`")
    A("")
    if k["gecti"]:
        A("✅ **GEÇTİ.** Ön kayıttaki kural sağlandı: OOS'ta eşit-ağırlık tabana "
          "göre POZİTİF `zayıf kanıt`. Faz 3-6 kurulur ve çıktı dili **ölçülmüş "
          "zayıf kenar** üzerine oturur — \"doğrulandı\" değil, \"zayıf kanıt\".")
    else:
        A("🛑 **GEÇMEDİ.** Ön kayıttaki kural sağlanmadı ve **ikinci tur yok**. "
          "Plan gereği doğrudan yeniden çerçeveleme: sistem \"izleme + risk "
          "disiplini + haber/veto aracı\" olarak tamamlanır, kenar iddia etmez, "
          "seviyeleri planlama geometrisi olarak sunar. Faz 3-6 yine kurulur; "
          "değişen tek şey çıktının DİLİDİR.")
    A("")
    A(f"> Çoklu test muhasebesi: teşhis adımında {r['n_teshis_test']} karşılaştırma "
      f"yapıldı, bu tur {r['n_test']} tane daha ekliyor. "
      f"{stats.bonferroni_note(r['n_teshis_test'] + r['n_test'])}")
    A("")
    A("> Bu sistemde en güçlü hüküm `zayıf kanıt`tır; \"doğrulandı\" dalı YOKTUR.")
    return "\n".join(L)


def evaluate_report(cfg: dict, e: dict) -> str:
    """Değerlendirme raporu — HIZLI DÖNGÜ.

    ⚠ Bu raporun en önemli davranışı ERKEN KENAR İDDİA ETMEMESİDİR. Her hüküm
    `edge_verdict`ten geçer; ilk ~18 ay `ölçüm yetersiz` yazacaktır ve bu
    doğru davranıştır. Erken kenar iddia ederse kod yalan söylüyordur
    (`tests/test_evaluate.py::test_sahte_alfa_erken_kenar_iddia_etmez`).
    """
    return "\n".join(
        [f"# Değerlendirme Raporu — {bugun()}", "",
         f"> {cfg['rapor']['uyari']}", ""] + _evaluate_govde(cfg, e))


def evaluate_report_all(cfg: dict, hepsi: dict) -> str:
    """TÜM kaynaklar tek belgede — ama HİÇBİR metrik toplanmadan.

    ⚠ Neden gerekliydi: `evaluate.run` birden çok kaynak varken
    `KaynakKarisik` fırlatıyor ve elle koşulan `bist degerlendir` çıkmaz sokağa
    düşüyordu. Sonuç: canlı analistlerin çözülmüş kararları HİÇBİR raporda
    görünmüyordu — beş bağımsız dış inceleme "raporlar donmuş" alarmı verdi;
    oysa raporlar donuk değildi, yalnız tek bir kaynağı (replay) gösteriyordu.

    Kural KORUNUYOR: kaynaklar karıştırılmaz. Burada yan yana basılırlar,
    hiçbir sayı toplanmaz ve her bölüm kendi N'ini taşır — `replay` VEKİL bir
    analisttir ve alfası gerçek LLM kayıtlarıyla aynı potaya girmez.
    """
    kaynaklar = hepsi["kaynaklar"]
    L = [f"# Değerlendirme Raporu — {bugun()}", "",
         f"> {cfg['rapor']['uyari']}", ""]
    A = L.append

    A(f"**{len(kaynaklar)} kaynak ayrı ayrı ölçüldü — hiçbiri toplanmadı.**")
    A("")
    A("| Kaynak | çözülmüş karar | alfa N | alfa | **HÜKÜM** |")
    A("|---|---|---|---|---|")
    for e in kaynaklar:
        a = e["alfa"]
        A(f"| `{e['tool']}` | {hepsi['sayim'].get(e['tool'], '—')} | {a['n']} | "
          f"{_s(a['ort'], 2, 'pp')} | **{a['hukum']}** |")
    A("")
    A("> `replay` VEKİL bir analisttir (kasten aptal, deterministik bir kural). "
      "Satırları KIYASLANABİLİR DEĞİLDİR: farklı araçlar farklı dönemlerde ve "
      "farklı N ile ölçülür. Tablo bir sıralama değil, bir DÖKÜMDÜR.")
    A("")
    for e in kaynaklar:
        A("---")
        A("")
        L += _evaluate_govde(cfg, e, baslik_seviyesi=3)
    return "\n".join(L)


def _evaluate_govde(cfg: dict, e: dict, *, baslik_seviyesi: int = 2) -> list[str]:
    """Tek kaynağın gövdesi. Hem tekil hem toplu rapor bunu kullanır —
    ikisi ayrışırsa biri diğerinin göstermediği bir şeyi gösterir."""
    h = "#" * baslik_seviyesi
    L: list[str] = []
    A = L.append
    a, ic, llm, tax = e["alfa"], e["ic"], e["llm_katkisi"], e["taksonomi"]

    if baslik_seviyesi > 2:
        A(f"{'#' * (baslik_seviyesi - 1)} Kaynak: `{e['tool']}`")
        A("")
    A(f"Kaynak: `{e['tool']}` · yılda ~{e['donem_yil']:.0f} bağımsız dönem üretiliyor")
    A("")

    A(f"{h} Ana metrikler")
    A("")
    A("| Metrik | N | değer | t | gerekli N | **HÜKÜM** |")
    A("|---|---|---|---|---|---|")
    A(f"| Eşleştirilmiş alfa (vs EW) | {a['n']} | {_s(a['ort'], 2, 'pp')} | "
      f"{_s(a['t'])} | {_n(a['gerekli_n'])} | **{a['hukum']}** |")
    A(f"| Dönem-içi IC (tüm kesit) | {ic['n_donem']} | {_s(ic['ic_ort'], 3)} | "
      f"{_s(ic['t'])} | {_n(ic['gerekli_n'])} | **{ic['hukum']}** |")
    A(f"| LLM katkısı (IC farkı) | {llm['n']} | {_s(llm['ort'], 3)} | "
      f"{_s(llm['t'])} | {_n(llm['gerekli_n'])} | **{llm['hukum']}** |")
    A("")
    A(f"`gerekli N` = t=2'ye ulaşmak için gereken **bağımsız dönem** sayısı. "
      f"Yıla çevirmek için {e['donem_yil']:.0f}'e böl.")
    A("")
    if a["xu100_ort"] is not None:
        A(f"XU100'e göre alfa {_s(a['xu100_ort'], 2, 'pp')} — **karar için "
          f"kullanılmaz**, sermaye-ağırlık eğilimi içerir (ADR #002).")
        A("")

    A(f"{h} Uygulanabilirlik (en hızlı ölçülen)")
    A("")
    sl = e["slippage"]
    A(f"- **Slippage** (planlanan giriş vs gerçekleşen dolum): "
      f"ort {_s(sl['ort'], 3, '%')} · N={sl['n']}")
    A(f"- **Tetiklenmeme oranı:** %{_s(tax['tetiklenmeme_orani'], 1)} "
      f"({tax['sonuc'].get('giris_olmadi', 0)}/{tax['toplam']} plan hiç dolmadı)")
    A("")

    A(f"{h} Sonuç ve hata dağılımı")
    A("")
    A("| Sonuç | n |   | Hata etiketi | n |")
    A("|---|---|---|---|---|")
    sonuclar = sorted(tax["sonuc"].items(), key=lambda x: -x[1])
    hatalar = sorted(tax["hata_etiketi"].items(), key=lambda x: -x[1])
    for i in range(max(len(sonuclar), len(hatalar))):
        s1 = f"{sonuclar[i][0]} | {sonuclar[i][1]}" if i < len(sonuclar) else " | "
        s2 = f"{hatalar[i][0]} | {hatalar[i][1]}" if i < len(hatalar) else " | "
        A(f"| {s1} |  | {s2} |")
    A("")

    A(f"{h} Güven kalibrasyonu (Brier)")
    A("")
    b = e["brier"]
    A(f"Brier skoru: {_s(b['brier'], 4)} · N={b['n']} · **{b['hukum']}**")
    if b["kovalar"]:
        A("")
        A("| Güven | n | iddia edilen | gerçekleşen |")
        A("|---|---|---|---|")
        for k in b["kovalar"]:
            A(f"| {k['seviye']} | {k['n']} | {_s(k['iddia'], 2)} | "
              f"{_s(k['gerceklesen'], 2)} |")
    A("")
    A(f"> {b['not']}")
    A("")

    A(f"{h} Rejim boyutlandırması işe yarıyor mu?")
    A("")
    bz = e["boyutlandirma"]
    A(f"Portföy katkısı farkı: {_s(bz['ort'], 3, 'pp')} · N={bz['n']} · "
      f"t={_s(bz['t'])} · **{bz.get('hukum', '—')}**")
    A("")
    A(f"> {bz['not']}")
    A("")
    A("_Bu satır uzun süre TANIM GEREĞİ sıfırdı (`ret_pct_equal_size` kolonu "
      "`ret_pct`'in kopyasıydı), yani rejim katmanı ölçülüyor görünüp hiç "
      "ölçülmüyordu — 2026-07-27 denetiminde düzeltildi (ADR #009)._")
    A("")

    A(f"{h} Veto")
    A("")
    v = e["veto"]
    A(f"- Veto sayısı: {v['veto_sayisi']}"
      + (f" — {v['veto_kodlari']}" if v["veto_kodlari"] else ""))
    A(f"- Seçilenlerin ortalama alfası: {_s(v['secilen_ort_alfa'], 2, 'pp')}")
    A(f"> {v['not']}")
    A("")

    A("---")
    A("")
    A(f"{h}# Bu raporun okunma kuralları")
    A("")
    A("- **`ölçüm yetersiz` bir sonuçtur, bir eksiklik değil.** Yanındaki büyük "
      "yüzde bir bulgu DEĞİLDİR.")
    A("- **Hüküm daima eşit-ağırlık evrene göre.** XU100 satırı bilgi içindir.")
    A("- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde \"doğrulandı\" YOKTUR.")
    A("- Ağırlıklar bu rapordan DEĞİŞMEZ — o yavaş döngünün işi (ADR #004).")
    return L


AZALT_SINYALLERI = ("reduce", "sell", "avoid")

#: Günlük fiyat marjı durumunun rapor hücresi. `None` "serbest" DEĞİLDİR —
#: değerlendirilmemiş bir durumu olumluya çevirmek L-007'nin yasakladığı şey.
_LIMIT_HUCRE = {
    "serbest": "serbest",
    "limite_yakin": "⚠ limite yakın",
    "kilitli": "🚧 **KİLİTLİ**",
    "limit_disi": "⚠ marj dışı (olağanüstü gün)",
    None: "— değerlendirilmedi",
}


def _limit_hucre(ld: dict | None) -> str:
    return _LIMIT_HUCRE.get((ld or {}).get("durum"), "— değerlendirilmedi")


def _kagit_portfoy_bolumu(cfg: dict, pf: dict, A) -> None:
    """§1a — kâğıt portföyün TL karnesi (ADR #019).

    Neden alfa/pp değil TL: bu bölümün sorusu "sıralama kalitesi" değil,
    **"10.000 TL ile ne oldu?"**. Karne (pp) seçilen planların ortalamasını
    ölçer; portföy ise KONTENJANIN, sektör tavanının ve tek-isim kuralının
    süzdüğü, gerçekten alınabilmiş olanları. İkisinin farkı bilgidir ve o
    yüzden reddedilen planlar da SEBEBİYLE basılır (L-020).
    """
    from . import portfoy as pfm

    # ⚠ Başlık h3: §1a ve §1b ZATEN DOLU (yürürlükteki vetolar / veto katkısı).
    # Yeni bir bölüm numarası araya sıkıştırmak, okuyucunun bildiği sıralamayı
    # kaydırırdı — rapor her gün aynı yerde aynı şeyi göstermeli.
    A("### Kâğıt karne — sistemin kendi kararlarıyla")
    A("")
    A(f"_Sistem {pfm.tl(pf['baslangic_sermaye'])} ile kendi kararlarını "
      "uyguluyormuş gibi takip ediyor (ADR #019). Emir gönderilmez; bu bir "
      "KAYIT katmanıdır ve seçime dokunmaz._")
    A("")
    A(f"**{pfm.tl(pf['sermaye'])}** · {pf['getiri_pct']:+.2f}% · "
      f"nakit {pfm.tl(pf['nakit'])} (%{pf['nakit_pct'] or 0:.0f}) · "
      f"gerçekleşen {pfm.tl(pf['gerceklesen_kar_try'])} · "
      f"{len(pf['pozisyonlar'])} açık / {len(pf['kapanan'])} kapandı")
    A("")

    if pf["pozisyonlar"]:
        A("| Hisse | adet | giriş | tarih | son | getiri | K/Z | stop | bariyer |")
        A("|---|---|---|---|---|---|---|---|---|")
        for p in pf["pozisyonlar"]:
            A(f"| {p['ticker']} | {p['adet']} | {_s(p['giris_fiyat'])} | "
              f"{p['giris_tarih']} | {_s(p['son_fiyat'])} | "
              f"{_s(p['getiri_pct'])}% | {pfm.tl(p['kar_try'])} | "
              f"{_s(p['stop_price'])} | {p['time_barrier_date']} |")
        A("")

    if pf["kapanan"]:
        A("**Kapanan işlemler**")
        A("")
        A("| Hisse | giriş → çıkış | sonuç | adet | getiri | K/Z |")
        A("|---|---|---|---|---|---|")
        for k in pf["kapanan"]:
            A(f"| {k['ticker']} | {k['giris_tarih']} → {k['cikis_tarih']} | "
              f"`{k['sonuc']}` | {k['adet']} | {_s(k['ret_pct'])}% | "
              f"{pfm.tl(k['kar_try'])} |")
        A("")

    if pf["reddedilen"]:
        # ⚠ Bu liste raporun en bilgilendirici satırı olabilir: karne
        # "seçilen planlar" üzerinden konuşur, portföy "alınabilenler"
        # üzerinden. Aradaki fark burada duruyor ve SINIF KODUYLA yazılıyor.
        from collections import Counter
        c = Counter(r["sebep"] for r in pf["reddedilen"])
        A("**Alınmayan planlar** — karne ile portföyün farkı buradan doğar")
        A("")
        for sebep, n in sorted(c.items(), key=lambda x: (-x[1], x[0])):
            isimler = sorted({f"{r['ticker']} ({r['asof']})"
                              for r in pf["reddedilen"] if r["sebep"] == sebep})
            A(f"- **{n}×** {pfm.RED_ETIKET.get(sebep, sebep)} "
              f"(`{sebep}`): {' · '.join(isimler[:6])}"
              + (" …" if len(isimler) > 6 else ""))
        A("")


def daily_report(cfg: dict, bundle: dict, *, holdings: dict | None = None,
                 analiz: list[dict] | None = None, acik_plan: int = 0,
                 portfoy: dict | None = None) -> str:
    """Günlük markdown rapor — **AZALT bölümüyle başlar.**

    Ölçüldü (2026-07-26): alt kuyruk (−1.03pp) üst kuyruğun ~1.8 katı. Retail
    olarak açığa satamazsın, dolayısıyla sistemin en savunulabilir çıktısı
    "ne al" değil "elindekilerden hangisini azalt"tır. Rapor sırası bu ölçüme
    göre seçildi; çoğu perakende araç bunu ters yapar.

    ⚠ `analiz` (journal'daki o güne ait tahminler) VERİLMELİ. İlk sürüm yalnız
    paketi okuyordu; analistin tezi, karşı senaryosu, VETOSU ve sinyali
    Mert'in okuduğu belgeye HİÇ ulaşmıyordu (2026-07-27 denetimi). Üstelik
    "azaltma adayları" başlığının altında azaltma kararı değil, düz bir
    envanter tablosu vardı. ADR #008 sonrası sistemin kalan ürünü veto ve
    haber yorumu; raporda görünmeyen bir ürün yoktur.
    """
    L: list[str] = []
    A = L.append
    r = bundle["rejim"]
    tutulan = holdings or {}
    an = {a["ticker"]: a for a in (analiz or [])}

    A(f"# BIST Günlük — {bundle['asof']}")
    A("")
    A(f"> ⚠ {bundle['uyari']}")
    A(f"> {cfg['rapor']['uyari']}")
    A("")
    A(f"**Rejim: {r['etiket']}** · nakit %{r['pozisyon_politikasi']['nakit_pct']:.0f} "
      f"· maks {r['pozisyon_politikasi']['maks_pozisyon']} pozisyon"
      + (f" · genişlik {_s(r.get('genislik_sma50_ustu_pct'), 1, '%')} "
         f"({r.get('genislik_n')}/{r.get('genislik_istenen_n')} isim)"
         if r.get("genislik_n") else ""))
    # Etiket TEK BAŞINA yanıltıcı: kural asimetrik (risk-on iki koşulu birden
    # ister, risk-off birine yeter) ve ölçüldü — 16 risk-off etiketinin 14'ü
    # yalnız genişlikten geldi, üstelik XU100 SMA200'ün ÜSTÜNDEYKEN. Rejimi
    # okuyan "endeks düşüyor" sanıyordu. Politika DEĞİŞMEDİ, yalnız ifşa edildi.
    if r.get("tetikleyici"):
        A("")
        A(f"_Tetikleyen: {r['tetikleyici']}_")
    if not analiz:
        A("")
        A("> ⚠ **Analist çıktısı yok** — bu rapor yalnız deterministik katmanı "
          "gösteriyor. Tez / veto / sinyal için önce `bist kaydet`.")
    hs = bundle.get("haber_taramasi") or {}
    if hs and not hs.get("ok", True):
        A("")
        A(f"> ⚠ **Haber katmanı güvenilmez:** {hs.get('not')} — aşağıdaki boş "
          "haber listeleri 'bildirim yok' anlamına GELMEZ.")
    A("")

    # --------------------------------------------------- 0) SIRALI EYLEM LİSTESİ
    # ADR #015. Raporun en üstünde TEK bir sıralı liste. ⚠ Sıra bir GETİRİ
    # sırası DEĞİL, uygulanabilirlik ve risk sırasıdır — başlık bunu taşır.
    from . import eylem as _ey
    sr = _ey.siralama(bundle, holdings=tutulan, analiz=analiz)
    A("## 0. Bugün yapılabilir işler — sırayla")
    A("")
    A("_Sıra **uygulanabilirlik ve risk** sırasıdır, bir getiri sırası DEĞİL "
      "(ADR #015). Hiçbir satır bir yön iddiası taşımaz; hepsi \"bu bugün "
      "yapılabilir mi ve neyi riske eder\" sorusunu cevaplar._")
    A("")
    if sr["kontenjan"] is not None:
        A(f"**Kontenjan:** {sr['tutulan_n']}/{sr['maks_pozisyon']} pozisyon dolu "
          f"→ rejim (`{sr['rejim']}`) **{sr['kontenjan']}** yeni pozisyona izin "
          f"veriyor · hedef nakit %{_s(sr['nakit_pct'], 0)}")
        # ⚠ Kontenjan `holdings`ten sayılır, journal'daki AÇIK PLANLARDAN değil.
        # 2026-08-11 denetimi: 9 açık `plan_sec` varken portföy boştu ve bu satır
        # "0/2 dolu" diyordu. Sonuç: KRDMD beş gün üst üste seçildi; planlar
        # harfiyen uygulansa tek isimde %26.9 birikirdi — rejim tavanı TOPLAM
        # %20 hisseyken. Sayı düzeltilmiyor (portföyü sistem bilemez), ama
        # aradaki fark artık GÖRÜNÜR.
        if acik_plan and not tutulan:
            A("")
            A(f"> ⚠ Journal'da **{acik_plan} açık plan** var ama portföyde "
              "kayıtlı pozisyon yok. Yukarıdaki kontenjan portföyden sayılır, "
              "yani şu an KÖR. `bist portfoy ekle <HİSSE> <adet> <maliyet>`")
        A("")
    if not sr["analist_var"]:
        A("> ⚠ Analist çıktısı yok — \"azalt\" satırları YALNIZ deterministik "
          "engellerden gelir. Boş bir azaltma listesi \"azaltacak bir şey yok\" "
          "anlamına GELMEZ.")
        A("")

    _sira = 0
    for kume, etiket in (("azalt", "ELDEKİLER"), ("gir", "YENİ GİRİŞ"),
                         ("izle", "İZLE / BEKLE")):
        if not sr[kume]:
            continue
        A(f"**{etiket}**")
        A("")
        for x in sr[kume]:
            _sira += 1
            isaret = "🔻" if x.tur == "azalt" else ("🟢" if x.tur == "gir" else "👀")
            satir = f"{_sira}. {isaret} **{x.ticker}** — {x.baslik}"
            if x.plan_id:
                satir += (f" · `{x.plan_id}` · riske edilen "
                          f"%{_s(x.riske_edilen_pct, 2)} · R:R net {_s(x.rr_net)}")
            A(satir)
            for g in x.gerekce:
                if g:
                    A(f"   - {g}")
            for g in x.engeller:
                A(f"   - 🚧 {g}")
        A("")
    if sr["engelli"]:
        A(f"**BUGÜN YAPILAMAZ ({len(sr['engelli'])})** — "
          + "; ".join(f"{x.ticker} ({x.engeller[0]})" for x in sr["engelli"]))
        A("")
    if not (sr["azalt"] or sr["gir"] or sr["izle"]):
        A("_Bugün sıralanacak uygulanabilir bir iş yok._")
        A("")

    # --------------------------------------------------- 1) AZALT (önce)
    #
    # ⚠ BAŞLIK SÖZLEŞMEDİR, DEĞİŞTİRİLMEZ. İlk denemede buraya "Portföy —
    # kâğıt karne ve azaltma adayları" yazıldı ve DÖRT sözleşme testi birden
    # kırmızıya döndü (`test_dokuman`, `test_uctan_uca`, `test_cli`). Haklıydılar:
    # "AZALT önce" bir estetik tercih değil, ölçüm sonucudur (alt kuyruk üst
    # kuyruğun ~1.8 katı) ve kâğıt karne bir DURUM bölümüdür, eylem değil.
    # Karne bu yüzden azaltma tablosunun ALTINDA duruyor.
    A("## 1. Elindekiler — azaltma adayları")
    A("")
    if not tutulan:
        A("_Portföyde kayıtlı pozisyon yok._ `bist portfoy ekle THYAO 100 312.5` "
          "ile ekleyebilirsin — sistemin en savunulabilir çıktısı bu bölüm ve "
          "neyi tuttuğunu bilmeden çalışamaz."
          if portfoy is None else
          "_Ne kâğıt portföyde ne elle girilmiş bir pozisyon var._ "
          "Kâğıt portföyün neden boş olduğu §1a'da sebebiyle yazılı.")
    else:
        A("| Hisse | adet | kapanış | **sinyal** | işlem görebilirlik | "
          "veri kalitesi | plan durumu |")
        A("|---|---|---|---|---|---|---|")
        ev = {e["ticker"]: e for e in bundle["evren"]}
        for t, h in sorted(tutulan.items()):
            e = ev.get(t, {})
            vk = e.get("veri_kalitesi") or {}
            kal = ("OK" if vk.get("ok")
                   else ("⚠ " + "; ".join(vk.get("uyarilar") or ["bilinmiyor"])))
            durum = ("plan var" if e.get("plan_menusu")
                     else (e.get("plan_yok_nedeni") or "evrende değil"))
            a = an.get(t)
            sinyal = a["signal"] if a else "—"
            if a and a["signal"] in AZALT_SINYALLERI:
                sinyal = f"**{sinyal.upper()}**"
            A(f"| {t} | {h['qty']:.0f} | "
              f"{_s((e.get('fiyat') or {}).get('kapanis'))} | {sinyal} | "
              f"{_limit_hucre(e.get('limit_durumu'))} | {kal} | {durum} |")

        kilitli = [t for t in sorted(tutulan)
                   if ((ev.get(t, {}).get("limit_durumu") or {}).get("durum")
                       == "kilitli")]
        if kilitli:
            A("")
            A(f"🚧 **{', '.join(kilitli)} tavana/tabana kilitli kapandı.** Karşı "
              "taraf boş demektir: azaltmak istesen de bugünkü fiyattan alıcı "
              "bulamayabilirsin ve bu kapanış gerçek denge fiyatı değildir. "
              "Bu isimlerde plan geometrisi de üretilmedi.")

        azalt = [an[t] for t in sorted(tutulan)
                 if t in an and an[t]["signal"] in AZALT_SINYALLERI]
        if azalt:
            A("")
            A("**Azaltma gerekçeleri (analistten):**")
            A("")
            for a in azalt:
                A(f"- **{a['ticker']}** — `{a['signal']}` · güven "
                  f"`{a['confidence']}`")
                A(f"  - _tez:_ {a['thesis']}")
                A(f"  - _karşı senaryo:_ {a['counter_scenario']}")
                A(f"  - _yanlışlayıcı:_ {a['falsifier']}")
        elif an:
            A("")
            A("_Analist elindekilerin hiçbirinde `reduce`/`sell`/`avoid` demedi._")
    A("")

    # Kâğıt karne AZALTMADAN SONRA — yukarıdaki uyarıya bak.
    if portfoy is not None:
        _kagit_portfoy_bolumu(cfg, portfoy, A)

    # --------------------------------------------------- 1a) AKTİF VETOLAR
    # Süresi dolmamış, ÖNCEKİ koşulardan kalan vetolar. Bunlar bugünkü analiz
    # olmasa da geçerlidir — vetonun ömrü artık koşuya değil takvime bağlı.
    aktif = [(e["ticker"], e["aktif_vetolar"]) for e in bundle["evren"]
             if e.get("aktif_vetolar")]
    if aktif:
        A("## 1a. Yürürlükteki vetolar (önceki günlerden)")
        A("")
        A("_Veto artık tek koşuya bağlı değil: süresi dolana kadar yürürlükte "
          "kalır. Bugün analiz koşmasan bile bunlar geçerlidir._")
        A("")
        # ⚠ Sütun eskiden "tekrar → 3× üst üste" diyordu. `journal.aktif_vetolar`
        # SÜRESİ DOLANI eliyor, yani saydığı şey ardışık bir seri değil,
        # BUGÜN HÂLÂ YÜRÜRLÜKTE olan tekrar sayısı. Bu yüzden veto yeniden
        # konmadan sayı 3'ten 2'ye DÜŞEBİLİYORDU ve okuyan bunu sayaç hatası
        # sanıyordu. Sayaç doğruydu; etiket yanlıştı (L-003).
        A("| Hisse | veto | son konuldu | bitiş | kalan | yürürlükteki tekrar |")
        A("|---|---|---|---|---|---|")
        for t, vs in aktif:
            for v in vs:
                A(f"| {t} | `{v['veto_code']}` | {v['konuldu']} | {v['bitis']} "
                  f"| {v['kalan_islem_gunu']} işlem günü"
                  + (f" | {v['tekrar']}× yürürlükte |" if v.get("tekrar", 1) > 1
                     else " | — |"))
        A("")

    # --------------------------------------------------- 1b) VETO
    vetolar = [a for a in (analiz or []) if a.get("veto_code")]
    if vetolar:
        A("## 1b. Vetolar — analistin en ölçülebilir katkısı")
        A("")
        A("_Veto gerçek bir karardır ve performansı AYRI ölçülür: veto "
          "edilenler seçilenlerden iyi giderse veto negatif değerlidir ve "
          "kapatılır (`bist degerlendir`)._")
        A("")
        # Basılan alan `key_risk` — vetonun GEREKÇESİ değil, analistin gördüğü
        # ana risk. İkisi farklı şeyler ve etiketsiz basıldığında okuyan bunu
        # tez sanıyordu (bir dış inceleme "yanlış değişken bağlanmış" diye
        # raporladı — değişken doğruydu, etiket yoktu).
        for a in vetolar:
            A(f"- **{a['ticker']}** · `{a['veto_code']}` — "
              f"_ana risk:_ {a['key_risk']}")
        A("")

    # --------------------------------------------------- 2) plan menüsü
    planli = [e for e in bundle["evren"] if e["plan_menusu"]]
    A(f"## 2. Plan geometrisi ({len(planli)} hisse)")
    A("")
    A("_Bunlar **öneri değil**, ölçülmüş kurallarla üretilmiş plan iskeletleridir. "
      "Kenar iddiası taşımazlar._")
    A("")
    # ⚠ PAY ve PAYDA GÖSTERİLEN PLANA AİT. Eskiden payda TÜM aday planları
    # sayıyordu (`sum(len(plan_menusu))`) ama gövde her hisseden yalnız
    # `plan_menusu[0]`'ı basıyor. Sonuç: 2026-07-30 raporu "3/7 plan
    # above_zone" diyordu, ekranda 3 plan vardı ve ÜÇÜ DE `in_zone`'du —
    # okuyan hiç göremediği bir oranı doğrulamaya çalışıyordu. Aday sayısı
    # bilgi olarak duruyor ama paydaya girmiyor.
    gosterilen = [e["plan_menusu"][0] for e in planli]
    tetiklenmeyen = sum(1 for p in gosterilen
                        if p.get("entry_zone_status") == "above_zone")
    aday_plan = sum(len(e["plan_menusu"]) for e in planli)
    if gosterilen:
        A(f"⚠ **{tetiklenmeyen}/{len(gosterilen)} plan `above_zone`** "
          f"({aday_plan} aday içinden gösterilen) — yani fiyat "
          "giriş bandının üstünde ve plan bir GERİ ÇEKİLMEYE bağlı. Ölçüldü "
          "(replay): planların **%46'sı hiç tetiklenmedi**. R:R değerleri "
          "planlar arasında KIYASLANABİLİR DEĞİLDİR (`rr_secim` alanına bak): "
          "hedef sabittir, eşitsizlik girişi aşağı iterek sağlanır.")
        A("")
    for e in planli:
        p = e["plan_menusu"][0]
        t1 = p["targets"][0] if p["targets"] else {}
        A(f"**{e['ticker']}** ({e['sektor']}) — kapanış {e['fiyat']['kapanis']}")
        A(f"- `{p['plan_id']}` {p['kind']} · giriş {p['entry_low']}–{p['entry_high']} "
          f"({p['entry_zone_status']}) · stop {p['stop_price']} "
          f"({p['stop_atr_multiple']}×ATR)")
        A(f"- T1 {t1.get('price')} · R:R **{t1.get('rr')} brüt / "
          f"{t1.get('rr_net')} net** (%{p.get('maliyet_pct')} gidiş-dönüş maliyet "
          f"düşülmüş) · dayanak: {t1.get('basis')}")
        A(f"- boyut %{p['position_size_pct']} · maks kayıp "
          f"%{p['max_loss_pct_of_portfolio']}")
        A(f"- {p['daily_limit_note']}")
        bp = e.get("bilanco_penceresi") or {}
        if bp.get("durum") == "acik":
            A(f"- 📅 **BİLANÇO PENCEREDE:** {bp['not']}"
              + ("" if not bp.get("bildirimler") else " — "
                 + "; ".join(f"{b['subject']} {b['start_date']}→{b['end_date']}"
                             for b in bp["bildirimler"][:2])))
        elif bp.get("durum") == "bilinmiyor":
            A(f"- ❔ Bilanço penceresi bilinmiyor: {bp.get('not')}")
        if p.get("rr_secim"):
            A(f"- _R:R nasıl sağlandı:_ {p['rr_secim']}"
              + (f" · elenen: {len(p.get('elenen_adaylar') or [])} aday"
                 if p.get("elenen_adaylar") else ""))
        a = an.get(e["ticker"])
        if a:
            A(f"- **analist:** `{a['signal']}` / `{a['action']}`"
              + (f" · VETO `{a['veto_code']}`" if a.get("veto_code") else "")
              + f" · güven `{a['confidence']}`")
            A(f"  - _tez:_ {a['thesis']}")
            A(f"  - _ana risk:_ {a['key_risk']}")
        A("")

    # --------------------------------------------------- 3) plan yok
    planyok = [e for e in bundle["evren"] if not e["plan_menusu"]]
    if planyok:
        A(f"## 3. Plan üretilmeyenler ({len(planyok)})")
        A("")
        # ⚠ Eskiden burada tek bir cümle vardı ve 15 ismin hepsi aynı metni
        # alıyordu: "stop∈[1.5,4.0]×ATR + R:R≥1.5 kurallarını BİRLİKTE
        # sağlayamadı". Teknik olarak doğruydu ama 2026-08-12 huni teşhisinde
        # 15/15'inde stop bandı GEÇMİŞTİ; öldüren tek şey hedefin fiyata çok
        # yakın olmasıydı. "Birlikte" kelimesi okuyanı yanlış yere baktırıyordu.
        A("_Gerekçe sınıfla basılır: `hedef çok yakın` ile `stop bandı tutmadı` "
          "aynı olgu değildir ve aynı cümleyle raporlanamaz (L-003)._")
        A("")
        from . import planner as _pl
        gruplar: dict[str, list[dict]] = {}
        for e in planyok:
            gruplar.setdefault(e.get("plan_yok_detay") or "?", []).append(e)
        # Sıra: en kalabalık sınıf üstte — okuyanın ilk gördüğü şey baskın
        # sebep olsun. Eşitlikte kod sırası (determinizm).
        for detay, grup in sorted(gruplar.items(),
                                  key=lambda kv: (-len(kv[1]), kv[0])):
            etiket = _pl.PLAN_YOK_ETIKET.get(detay, detay)
            A(f"**{etiket}** ({len(grup)})")
            A("")
            for e in grup:
                A(f"- **{e['ticker']}** — {e['plan_yok_nedeni']}")
                for x in (e.get("plan_yok_elenen") or [])[:3]:
                    A(f"  - _elenen:_ {x}")
            A("")
    return "\n".join(L)


def telegram_ozet(cfg: dict, bundle: dict, *, analiz: list[dict] | None = None,
                  holdings: dict | None = None, cozulen: list[dict] | None = None,
                  analist_model: str | None = None,
                  saglik: str | None = None,
                  portfoy: dict | None = None) -> str:
    """Telefonda okunacak KISA özet (Faz 8).

    Tam rapor `reports/` altında ve repoda duruyor; bunun işi onu tekrarlamak
    değil, **bakılmaya değer bir şey olup olmadığını** söylemek. Bu yüzden
    tasarım kuralı: bildirimin uzunluğu O GÜN OLAN BİTENLE orantılı olsun.
    Sakin bir günde üç satır çıkar; veto/plan/çözüm varsa uzar.

    Sıra tam raporla AYNI ve aynı ölçüme dayanıyor (ADR: alt kuyruk üst
    kuyruğun 1.8 katı): önce elindekiler, sonra veto, en sonda yeni plan.
    Bildirimi "ne al" ile başlatmak, ölçümün söylediğinin tersi olurdu.
    """
    r = bundle["rejim"]
    pol = r["pozisyon_politikasi"]
    an = {a["ticker"]: a for a in (analiz or [])}
    tutulan = holdings or {}
    L: list[str] = []
    A = L.append

    A(f"📊 BIST — {bundle['asof']}")
    A(f"Rejim: {r['etiket']} · nakit %{pol['nakit_pct']:.0f} · maks "
      f"{pol['maks_pozisyon']} pozisyon")
    if saglik:
        A(saglik)

    # 0) KÂĞIT PORTFÖY — tek satır (ADR #019). Rejim satırının hemen altında
    # duruyor çünkü ikisi aynı soruyu cevaplıyor: "şu an neredeyiz?". Sistemin
    # kendi karnesi, bildirimin en somut satırıdır — pp değil TL konuşur.
    if portfoy:
        from . import portfoy as pfm
        A(f"💼 {pfm.tl(portfoy['sermaye'])} ({portfoy['getiri_pct']:+.2f}%) · "
          f"{len(portfoy['pozisyonlar'])} açık · nakit %{portfoy['nakit_pct'] or 0:.0f}")

    # 1) Elindekiler — azaltma sinyali varsa ÖNCE o
    azalt = [t for t, a in an.items()
             if t in tutulan and a.get("signal") in ("reduce", "sell", "avoid")]
    if azalt:
        A("")
        A(f"⚠️ AZALT: {', '.join(sorted(azalt))}")

    # 2) Veto — analistin en ölçülebilir katkısı
    vetolar = [(t, a.get("veto_code")) for t, a in sorted(an.items())
               if a.get("action") == "plan_reddet"]
    if vetolar:
        A("")
        A("🚫 Veto: " + " · ".join(f"{t} ({v})" for t, v in vetolar))

    # 3) Seçilen planlar
    secilen = [t for t, a in sorted(an.items()) if a.get("action") == "plan_sec"]
    if secilen:
        A("")
        A(f"📌 Plan seçildi: {', '.join(secilen)}")

    # 4) Bugün kapanan tahminler — "sistem kendi karnesini de bildirir"
    if cozulen:
        ozet: dict[str, int] = {}
        for c in cozulen:
            k = c.get("resolution", "?")
            ozet[k] = ozet.get(k, 0) + 1
        A("")
        A("✅ Çözülen: " + " · ".join(f"{k}={v}" for k, v in sorted(ozet.items())))

    if not analiz:
        A("")
        A("ℹ️ Analist çıktısı yok — yalnız deterministik katman.")
    elif analist_model:
        A("")
        A(f"🤖 {analist_model}")

    A("")
    A("Ölçülen kenar yok — plan geometrisi, yön iddiası değil.")
    return "\n".join(L)


def write(cfg: dict, ad: str, icerik: str) -> str:
    """Raporu `reports/` altına yazar ve yolu döner."""
    p = util.ensure_parent(f"{cfg['paths']['reports_dir']}/{ad}")
    p.write_text(icerik + "\n", encoding="utf-8")
    return str(p)


def bugun() -> str:
    return date.today().isoformat()
