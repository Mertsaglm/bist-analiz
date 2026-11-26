# PROJECT.md — Projenin Kimliği

Güncel devir [STATE](STATE.md), dokümanlar [proje haritasında](../docs/PROJE-ICINDEKILER.md), son araştırma [25 Kasım denetiminde](../docs/TAHMIN-DENETIMI-2026-11-25.md).

## Araştırma yaklaşımı — 2026-11-24

Mevcut ana strateji ve eş bütçeli pasif kol referanstır. Kontrollü rakipler
ayrı sanal hesaplarda veya zaman sıralı replay'de fiilen sınanır. Veri
güvenilirliği ve muhasebe kuralları ortak kalır. Trend, makas, R:R ve
tahsis ekonomik hipotezlerdir. Katkıdan arındırılmış net getiri, düşüş,
maliyet, kapsama ve reddedilen fırsatlar ön kayıtla izlenir. İlk deneme
üstünlük kanıtı gerektirmez. Ana politika için ileri ekonomik kanıt gerekir.
Ortak T0 yalnız ortak beş kolun başlangıcıdır. Bağımsız araştırmalar sürer.
İleri momentumun ilk 5/ilk 10, %8 tahsis ve %0,6 stop protokolü
[karar günlüğünde](DECISIONS.md). Özellik, vade veya karar semantiği
değişen ML adayına ayrı kimlik ve defter açılır. Mevcut tahmin mühürleri,
kaynak kesitleri ve vadeleri korunur.

25 Kasım tahmin araştırması iki piyasanın CPU tabanlı 5/20/60 seans
karşılaştırmasını ve 20 seanslık BIST gölge kaydını başlattı. Tahmin
doğruluğu, dağılım kalibrasyonu ve masraflı sanal servet ayrı ölçülür.
[Araştırma ve sonuçlar](../docs/TAHMIN-ARASTIRMASI-2026-11-25.md)

## Revizyon hedefi — 2026-11-19

BIST ve İş Bankası gram altını için iki ayrı otomatik sanal hesap. Her piyasa
50.000 TL ile başlar ve ayda 5.000 TL katkı alır. Hedef, banka maliyetlerinden
sonra serveti uygun AL/SAT kararlarıyla artırmak. Pasif kol aynı parayla
otomatik işler. Yeni modeller ayrı defterde otomatik ölçülür. Açık pozisyon
yeni fiyat, risk veya sinyal değişince yeniden değerlendirilir. Tahminin
ölçüm ufku, zorunlu pozisyon süresi olarak kullanılmaz. Yaklaşık saatlik
bulut gözlemi ve kısa gün sonu Telegram raporu, bilgisayar kapalıyken de
çalışmalıdır. Gerçek emir, elle rutin tetikleme ve ek harcama kapsam dışıdır.

## İşletim bütçesi — 2026-10-29

Mert ek ödeme yapamayacağını belirtti. Ücretli servis/LLM açılmaz, harcama limiti
artırılmaz ve özel depo herkese açılmaz. Eski düşük maliyet/LLM bütçe kararlarının
yerine geçer. BIST günlük otomasyonu V1 LLM olmadan veri/rapor üretir;
deterministik V2 çalışmaya devam eder. Saatlik gözlem stop kontrol sıklığını da
azaltır; gerçek zaman garantisi yok. Yerel hazırlık ve üretim kabulü ayrı tutulur.

## İleri sanal sınav kapsamı — 2026-10-01

Ana hesap geçmişi ve eski adaylar korunur. Ortak ileri T0 ile iki ayrı piyasada
50.000 TL + aylık 5.000 TL bütçeli beş yeni sanal kol kurulur. %80 çekirdek
düzenli birikimdir; BIST'te tarihli BIST30 eşit ağırlıklı sepet, altında İş Bankası
GRAM. En fazla %20 taktik, masraf sonrası tahmin ve açık stop riskiyle sınırlıdır.
Çekirdek + nakit/pasif kollar taktiğin ek katkısını ölçer. Eski Ridge kontrol,
göreli BIST/ons-kur altın Ridge ayrı model adayıdır. LightGBM yalnız offline'dır.
Başarı, aynı katkılarla maliyet sonrası servet ve katkısız getirinin pasif kola
göre değerlendirilmesidir. Düşüş daha kötü olmamalı. İlk T0 çevrimi tüm çekirdek
fiyatları ve taze kaynak kapanışıyla ekonomik ayarları mühürler.
[Portföy deneyi](../docs/PORTFOY-DENEYI-2026-10-01.md)
Yayın, ilk canlı çevrim ve T0 ön koşullarının güncel durumu `ai/STATE.md` dosyasındadır.

## Karar ölçümü — 2026-11-24

60 takvim günü yeni strateji alımı yoksa işlemsizlik incelemesi yapılır.
BEKLE ölçümü kapıları, masraf sonrası varsayımsal getiriyi, eşleşen pasif
kıyası ve eksik vade kotasyonunu gösterir. Zorunlu tahsis yalnız ayrı,
ön kayıtlı bir deney olarak değerlendirilebilir. Ortak T0 açılışı uygun
kotasyona, eş bütçeye ve iki piyasanın canlı kabulüne bağlıdır.

## Güncel kapsam — 2026-09-25

Mert'in yeni talebi: BIST ve İş Bankası gram altını için iki ayrı otomatik analiz ve
sanal portföy, ortak web paneli, kısa ve net Türkçe Telegram kararları. Amaç masrafları
hesaba katarak birikimin değerini, hisse/gram miktarlarını artıracak fırsatları izlemek.
Gerçek emir iletimi yok. Bütçe her hesapta 50.000 TL başlangıç + aylık 5.000 TL; faizsiz nakit.
Yeni bütçe ayrı hesap kimliğindedir. Sınırlı aday kataloğu ayrı defterlerde sınanır;
hiçbir adayın üstünlüğü peşinen kabul edilmez. Ayrıntı: `docs/REVIZYON-2026-09-25.md`.
Kullanıcının gerçek varlıkları bilinmediğinden yeni sanal hesaplara aktarılmadı.

`advisor/` güncel karar/defter hattıdır; `src/` eski veri toplama ve araştırma hattıdır.
Mevcut API anahtarları korunur. Sayısal karar bankaya özgü referans fiyat, masraf, trend,
risk ve zaman sıralı ölçüme dayanır. Kesin ifade eylemi belirtir; fiyat tahminine kesinlik
atfetmez. Yeni sonuçlar olgunlaşınca sınırlı hata düzeltmesi uygulanır.

Başarı tanımı: para korunumu ve tekrar çalıştırma testleri geçer; fiyat eksikliği görünür;
her işlem fiyatı ve masrafıyla izlenir; katkılar hariç getiri aynı bütçeli al-tut ile
karşılaştırılır. Ayrıntı: `docs/V2-REHBER.md`.

## Mimari ve teknik sınırlar

- `advisor/`: deterministik karar, model ve ayrı sanal olay defterleri.
  `src/`: çalışan V1 veri/araştırma/LLM hattı. V1 kâğıt portföyü V2 serveti değildir.
- `dashboard/` iki deponun son görünümünü okur; karar veya işlem yazmaz.
  Altın ayrı `../gold_tracking_system/` deposudur. Ortak motor eşliği
  `advisor/shared-manifest.json` ve `scripts/advisor_manifest.py` ile izlenir.
- Python 3.12, Poetry, SQLite ve deterministik SQL arşivi; macOS geliştirme,
  GitHub Actions üretim. Yerel SQLite ikilisi güncel üretim kanıtı sayılmaz.
- V1 veri kaynakları yfinance, KAP ve TCMB EVDS'dir. V2 BIST gecikmeli son
  fiyatı ve İş Bankası GRAM alış/satış referansını kullanır; gerçek dolum değildir.
- Eski defter/geçmiş ve API anahtarları korunur. Açılmış hesabın bütçesi
  geriye dönük değişmez; yeni bütçe/yöntem ayrı hesap veya deney kimliği alır.
- Katkı kâr, temettü alacağı ödeme gelmeden nakit sayılmaz. Eksik/bayat
  fiyat kesin servet veya sıfır zarar değildir; değerleme bilinmiyor kalır.
- Önceki tamamlanmış kapanış olmadan yeni alım yok; geçerli güncel fiyatla
  mevcut koruyucu çıkış ayrı değerlendirilir. Okunma saati yeni kotasyon değildir.
- Model eğitimi ve kalibrasyon zaman sıralıdır; sonuçlanmamış etiket veya
  replay canlı kanıt değildir. Mühürlü tahmin vadesi sonradan ayarla değişmez.
- Mühürlü ön kayıtlar (`docs/on-kayit-*.md`) değiştirilmez; başarısız sınav
  sonrası eşik gevşetilmez. Yeni adaylar ayrı ölçülür, otomatik terfi yapılmaz.

## V1 araştırma sınırları ve geçmiş

V1 ana ufku 20 işlem günü; plan geometrisi getiri üstünlüğü kanıtı değildir.
Python entry/stop/hedef/boyut menüsünü üretir; LLM plan seçer, veto ve yorum
verir, hesaplanabilir sayı üretmez. Sert çıktı denetimi ve değişmez journal korunur.
V1 birincil ölçüm tabanı aynı maliyetli eşit ağırlık evrenidir; XU100 yalnız
ikincil iletişim tabanıdır. Sektör nötralizasyonu ölçüm nedeniyle varsayılan kapalıdır.

Örtüşen günler ve aynı piyasa hareketindeki hisseler bağımsız örnek sayılmaz.
V1 değerlendirmesi `required_n()` ile ölçüm yeterliliğini açıklar; faktör
üstünlüğü kanıtlanmış değildir. Sabit eski evren/bütçe kuralları güncel V2'ye taşınmaz.
V1 iki-AI konsensüs, intraday veri, temel faktör ve sayısal haber skoru
kapsamında değildir; BIST Telegram bildirimi tek yönlüdür.

Araç bağımsızlığı korunur. ADR #013'teki yaklaşık $3/ay LLM tavanı tarihsel
karardır; 2026-10-29 sıfır ek ödeme talebi bunu geçersiz kılar. Üretim V1 LLM
kapalıdır. Eski maliyet ölçümü yeni model sırası için kanıt değildir (ADR #028).
Araştırma modeli ayarları `config.yaml` içindedir; otomatik yeniden açılmaz.

Eski kapsamın tam kaydı `ai/archive/PROJECT-V1-2026-10-01.md` dosyasındadır.
Karar gerekçeleri `ai/DECISIONS.md`, hata kayıtları `ai/LESSONS.md` içindedir.
