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
    L: list[str] = []
    A = L.append
    a, ic, llm, tax = e["alfa"], e["ic"], e["llm_katkisi"], e["taksonomi"]

    A(f"# Değerlendirme Raporu — {bugun()}")
    A("")
    A(f"> {cfg['rapor']['uyari']}")
    A("")
    A(f"Kaynak: `{e['tool']}` · yılda ~{e['donem_yil']:.0f} bağımsız dönem üretiliyor")
    A("")

    A("## Ana metrikler")
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

    A("## Uygulanabilirlik (en hızlı ölçülen)")
    A("")
    sl = e["slippage"]
    A(f"- **Slippage** (planlanan giriş vs gerçekleşen dolum): "
      f"ort {_s(sl['ort'], 3, '%')} · N={sl['n']}")
    A(f"- **Tetiklenmeme oranı:** %{_s(tax['tetiklenmeme_orani'], 1)} "
      f"({tax['sonuc'].get('giris_olmadi', 0)}/{tax['toplam']} plan hiç dolmadı)")
    A("")

    A("## Sonuç ve hata dağılımı")
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

    A("## Güven kalibrasyonu (Brier)")
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

    A("## Veto")
    A("")
    v = e["veto"]
    A(f"- Veto sayısı: {v['veto_sayisi']}"
      + (f" — {v['veto_kodlari']}" if v["veto_kodlari"] else ""))
    A(f"- Seçilenlerin ortalama alfası: {_s(v['secilen_ort_alfa'], 2, 'pp')}")
    A(f"> {v['not']}")
    A("")

    A("---")
    A("")
    A("### Bu raporun okunma kuralları")
    A("")
    A("- **`ölçüm yetersiz` bir sonuçtur, bir eksiklik değil.** Yanındaki büyük "
      "yüzde bir bulgu DEĞİLDİR.")
    A("- **Hüküm daima eşit-ağırlık evrene göre.** XU100 satırı bilgi içindir.")
    A("- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde \"doğrulandı\" YOKTUR.")
    A("- Ağırlıklar bu rapordan DEĞİŞMEZ — o yavaş döngünün işi (ADR #004).")
    return "\n".join(L)


def daily_report(cfg: dict, bundle: dict, *, holdings: dict | None = None) -> str:
    """Günlük markdown rapor — **AZALT bölümüyle başlar.**

    Ölçüldü (2026-07-26): alt kuyruk (−1.03pp) üst kuyruğun ~1.8 katı. Retail
    olarak açığa satamazsın, dolayısıyla sistemin en savunulabilir çıktısı
    "ne al" değil "elindekilerden hangisini azalt"tır. Rapor sırası bu ölçüme
    göre seçildi; çoğu perakende araç bunu ters yapar.
    """
    L: list[str] = []
    A = L.append
    r = bundle["rejim"]
    tutulan = holdings or {}

    A(f"# BIST Günlük — {bundle['asof']}")
    A("")
    A(f"> ⚠ {bundle['uyari']}")
    A(f"> {cfg['rapor']['uyari']}")
    A("")
    A(f"**Rejim: {r['etiket']}** · nakit %{r['pozisyon_politikasi']['nakit_pct']:.0f} "
      f"· maks {r['pozisyon_politikasi']['maks_pozisyon']} pozisyon")
    A("")

    # --------------------------------------------------- 1) AZALT (önce)
    A("## 1. Elindekiler — azaltma adayları")
    A("")
    if not tutulan:
        A("_Portföyde kayıtlı pozisyon yok._ `bist portfoy ekle THYAO 100 312.5` "
          "ile ekleyebilirsin — sistemin en savunulabilir çıktısı bu bölüm ve "
          "neyi tuttuğunu bilmeden çalışamaz.")
    else:
        A("| Hisse | adet | kapanış | veri kalitesi | plan durumu |")
        A("|---|---|---|---|---|")
        ev = {e["ticker"]: e for e in bundle["evren"]}
        for t, h in sorted(tutulan.items()):
            e = ev.get(t, {})
            kal = "OK" if (e.get("veri_kalitesi") or {}).get("ok", True) else "⚠ BOZUK"
            durum = ("plan var" if e.get("plan_menusu")
                     else (e.get("plan_yok_nedeni") or "evrende değil"))
            A(f"| {t} | {h['qty']:.0f} | "
              f"{_s((e.get('fiyat') or {}).get('kapanis'))} | {kal} | {durum} |")
    A("")

    # --------------------------------------------------- 2) plan menüsü
    planli = [e for e in bundle["evren"] if e["plan_menusu"]]
    A(f"## 2. Plan geometrisi ({len(planli)} hisse)")
    A("")
    A("_Bunlar **öneri değil**, ölçülmüş kurallarla üretilmiş plan iskeletleridir. "
      "Kenar iddiası taşımazlar._")
    A("")
    for e in planli:
        p = e["plan_menusu"][0]
        t1 = p["targets"][0] if p["targets"] else {}
        A(f"**{e['ticker']}** ({e['sektor']}) — kapanış {e['fiyat']['kapanis']}")
        A(f"- `{p['plan_id']}` {p['kind']} · giriş {p['entry_low']}–{p['entry_high']} "
          f"({p['entry_zone_status']}) · stop {p['stop_price']} "
          f"({p['stop_atr_multiple']}×ATR)")
        A(f"- T1 {t1.get('price')} (R:R {t1.get('rr')}, dayanak: {t1.get('basis')}) "
          f"· boyut %{p['position_size_pct']} · maks kayıp "
          f"%{p['max_loss_pct_of_portfolio']}")
        A(f"- {p['daily_limit_note']}")
        A("")

    # --------------------------------------------------- 3) plan yok
    planyok = [e for e in bundle["evren"] if not e["plan_menusu"]]
    if planyok:
        A(f"## 3. Plan üretilmeyenler ({len(planyok)})")
        A("")
        for e in planyok:
            A(f"- **{e['ticker']}** — {e['plan_yok_nedeni']}")
        A("")
    return "\n".join(L)


def write(cfg: dict, ad: str, icerik: str) -> str:
    """Raporu `reports/` altına yazar ve yolu döner."""
    p = util.ensure_parent(f"{cfg['paths']['reports_dir']}/{ad}")
    p.write_text(icerik + "\n", encoding="utf-8")
    return str(p)


def bugun() -> str:
    return date.today().isoformat()
