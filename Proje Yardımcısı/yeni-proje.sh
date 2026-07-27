#!/bin/bash
# Usta şablonunu yeni bir projeye kopyalar.
# Kullanım: ./yeni-proje.sh /yol/YeniProje
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Kullanım: ./yeni-proje.sh /yol/YeniProje"
  exit 1
fi

# ⚠ KAYNAK bu script'in klasörü DEĞİL, PROJE KÖKÜDÜR.
# L-004'te kural dosyaları alt klasörden köke taşındı (hiçbir IDE alt
# klasördeki AGENTS.md'yi okumuyordu) ama bu script güncellenmedi ve
# 2026-07-27 denetimine kadar HİÇ ÇALIŞMADI — "cp: No such file or directory".
# Tam olarak LESSONS L-002'nin deseni: elle çalıştırılan script sessizce donar.
KAYNAK="$(cd "$(dirname "$0")/.." && pwd)"
HEDEF="$1"

if [ ! -f "$KAYNAK/AGENTS.md" ]; then
  echo "HATA: '$KAYNAK/AGENTS.md' yok."
  echo "Bu script proje KÖKÜNÜN altındaki bir klasörden çalışmayı bekler."
  exit 1
fi

if [ -e "$HEDEF" ] && [ -n "$(ls -A "$HEDEF" 2>/dev/null)" ]; then
  echo "HATA: '$HEDEF' zaten var ve boş değil. Üzerine yazmamak için duruyorum."
  exit 1
fi

mkdir -p "$HEDEF/ai/archive" "$HEDEF/.github" "$HEDEF/docs"

# Kural dosyaları KÖKE kopyalanır — alt klasördekini hiçbir IDE okumaz (L-004).
cp "$KAYNAK/AGENTS.md"  "$HEDEF/"
cp "$KAYNAK/CLAUDE.md"  "$HEDEF/"
cp "$KAYNAK/GEMINI.md"  "$HEDEF/"
cp "$KAYNAK/.github/copilot-instructions.md" "$HEDEF/.github/"
# PROFILE ve LESSONS projeler arası TAŞINIR (Mert değişmiyor, dersler birikiyor).
cp "$KAYNAK/ai/PROFILE.md"  "$HEDEF/ai/"
cp "$KAYNAK/ai/LESSONS.md"  "$HEDEF/ai/"

# ⚠ PROJECT.md KOPYALANMAZ, BOŞ ŞABLON olarak kurulur. Kopyalamak, her yeni
# projeye kaynak projenin kimliğini taşırdı — ve Usta "PROJECT.md dolu" diye
# görüp keşif protokolünü hiç çalıştırmazdı (2026-07-27 denetiminde yakalandı).
cat > "$HEDEF/ai/PROJECT.md" <<'EOF'
# PROJECT.md — Projenin Kimliği

> Bir kez yazılır, nadiren değişir.
> ⚠ BOŞ ŞABLON. Usta `/baslat` ya da `/tanis` ile keşif protokolünü çalıştırıp
> BURAYI KENDİSİ DOLDURUR. Sen sadece anlatırsın.

## Proje Adı
_(doldurulacak)_

## Tek Cümlelik Amaç
_(doldurulacak — kim kullanacak, hangi derdi çözüyor?)_

## Başarı Kriteri
_(doldurulacak — "oldu bu iş" dedirtecek doğrulanabilir şey ne?)_

## Kapsam (Ne VAR — v1)
- _(doldurulacak)_

## Kapsam Dışı (Ne YOK — bilerek)
- _(doldurulacak — ve NEDEN bilerek dışarıda olduğu yazılır)_

## Kısıtlar
- **Bütçe:** _(doldurulacak)_
- **Zaman:** _(doldurulacak)_
- **Ortam:** _(doldurulacak)_

## En riskli varsayım
_(doldurulacak — "bu hiç çalışır mı?" sorusunu cevaplayan parça hangisi?)_

## Teknoloji Yığını
| Katman | Seçim | Karar kaydı |
|---|---|---|
| _(doldurulacak)_ | | |
EOF

# ⚠ `ai/archive/README.md` BURADA KOPYALANMAZ. Kopyalanıyordu, ama aşağıda
# kanonik içerikle zaten ÜZERİNE YAZILIYORDU — yani kopya ölüydü ve kaynakta o
# dosya yoksa script boşuna patlıyordu. İki yerden beslenen tek dosya, hangisinin
# kazandığı belirsiz bir dosyadır.

BUGUN="$(date +%Y-%m-%d)"

# docs/ — ön kayıtlar. Boş klasör git'te durmaz, açıklamayla birlikte kurulur.
cat > "$HEDEF/docs/README.md" <<'EOF'
# docs/ — ÖN KAYITLAR

Bir ölçüm/deney KOŞULMADAN ÖNCE buraya bir dosya yazılır:

1. Hipotez ve nereden geldiği (sezgiden değil, bir gözlemden)
2. Değişecek olanlar — YALNIZCA onlar
3. Değişmeyecek olanlar — açıkça
4. **Geçme şartı** — sonucu görmeden yazılır
5. Başarısızlık halinde ne olacak

Sonra dosyanın sha256'sı alınır ve koda gömülür; rapor onu basar.

**Neden:** Sonucu gördükten sonra çıtayı indirmek, ölçüm yapan her projede
en kolay ve en pahalı kendini kandırma yoludur. Ön kayıt onu imkânsız kılar.
Ölçüm yapmayan projelerde bu klasör boş kalır — sorun değil.
EOF

# STATE.md sıfırdan başlar
cat > "$HEDEF/ai/STATE.md" <<EOF
# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi \`ai/archive/STATE-YYYY-MM.md\`'ye taşı.

**Son güncelleme:** $BUGUN
**Aktif milestone:** Başlangıç

## ✅ Tamamlananlar
- $BUGUN — Proje şablondan oluşturuldu

## 🔨 Devam Edenler
- (yok)

## 🧱 Bloklar / Bekleyenler
- (yok)

## 🎯 Sıradaki 3 İş
1. /baslat yaz — Usta proje keşfini yapsın: sorular sorup ai/PROJECT.md'yi kendisi doldursun — DoD: PROJECT.md dolu ve onaylı
2. /plan ile ilk milestone'u çıkar — DoD: 1-2 saatlik görevler + DoD'ler hazır
3. En riskli varsayımı doğrulayan ilk görevi yap — DoD: "bu iş çalışır" kanıtlandı

## 📦 Backlog (şimdi değil, unutma da)
- (boş)
EOF

# Kural dosyalarının GERÇEKTEN yüklendiğini test etmeyi hatırlat (L-004).
cat > "$HEDEF/ai/archive/README.md" <<'EOF'
# archive/

STATE.md şiştiğinde (~100 satır) eski içerik buraya taşınır: `STATE-YYYY-MM.md`.
Usta bu klasörü yalnızca geçmişe dair özel bir soru gelirse okur —
normal oturumlarda bağlamı şişirmemek için okumaz.
EOF

# DECISIONS.md boş başlar (şablonla birlikte)
cat > "$HEDEF/ai/DECISIONS.md" <<'EOF'
# DECISIONS.md — Karar Günlüğü (ADR)

> Yalnızca ÖNEMLİ kararlar: mimari, araç, yaklaşım seçimleri.
> Her karar "neden"i ve "tekrar gözden geçirme koşulu" ile kaydedilir.
> En yeni karar en üste.

---

<!-- Yeni karar şablonu:

## #NNN — YYYY-MM-DD — Kısa başlık

**Bağlam:** Hangi sorun/ihtiyaç bu kararı doğurdu?

**Seçenekler:**
- A) ... → artı/eksi
- B) ... → artı/eksi

**Karar:** Seçilen şey.

**Neden:** Hangi kısıta/hedefe dayanarak?

**Tekrar gözden geçir:** Hangi koşul oluşursa bu karar masaya geri gelir?
-->
EOF

# ---------------------------------------------------------------- doğrulama
# ⚠ Kopya doğrulaması EN SONA alındı ve KAPSAMI GENİŞLETİLDİ.
#
# Eskiden yalnız kopyalanan altı dosyaya bakıyordu ve script'in ORTASINDAydı —
# yani sonradan ÜRETİLEN dosyalar (STATE, DECISIONS, docs/, archive/, copilot
# köprüsü) hiç kontrol edilmiyordu. Sessiz eksik dosya, kural sisteminin hiç
# devreye girmemesi demektir ve hata da vermez (L-004: yanlış yerdeki doğru
# dosya = yok hükmünde). Bir kontrolü kendi ürettiği şeyin ÖNÜNE koymak, o
# kontrolü yarısı kör bırakır.
ZORUNLU=(
  AGENTS.md
  CLAUDE.md
  GEMINI.md
  .github/copilot-instructions.md
  ai/PROJECT.md
  ai/PROFILE.md
  ai/LESSONS.md
  ai/STATE.md
  ai/DECISIONS.md
  ai/archive/README.md
  docs/README.md
)
for z in "${ZORUNLU[@]}"; do
  [ -s "$HEDEF/$z" ] || { echo "HATA: $z oluşturulamadı"; exit 1; }
done

# PROJECT.md BOŞ ŞABLON kalmalı — dolu gelirse Usta keşif protokolünü hiç
# çalıştırmaz ve yeni proje, kaynak projenin kimliğiyle başlar.
grep -q "doldurulacak" "$HEDEF/ai/PROJECT.md" \
  || { echo "HATA: PROJECT.md boş şablon değil"; exit 1; }

# Köprü dosyaları kural KOPYALAMAZ, AGENTS.md'ye YÖNLENDİRİR. Kuralı iki yere
# yazmak, iki farklı kural setine dönüşmesinin en kısa yoludur.
for k in CLAUDE.md GEMINI.md .github/copilot-instructions.md; do
  grep -q "AGENTS.md" "$HEDEF/$k" \
    || { echo "HATA: $k AGENTS.md'ye yönlendirmiyor"; exit 1; }
done

echo "✅ Hazır: $HEDEF"
echo
echo "Sıradaki adım: AI aracında projeyi aç ve '/baslat' yaz."
echo "Usta sana soruları sorup PROJECT.md'yi kendisi dolduracak."
echo
echo "⚠ İLK İŞ: '/durum' yazıp Usta'nın STATE.md'yi GERÇEKTEN okuduğunu doğrula."
echo "  Kural dosyası yüklenmezse sistem hata vermez, sadece sessizce"
echo "  devreye girmez (LESSONS L-004). Dosyanın varlığını görmek yeterli değil."
echo
echo "Not: Projede bir kural kesinleştiğinde AGENTS.md bölüm 12'ye bak —"
echo "  'yorum bir niyettir, test bir sözleşmedir'. Yalnız yorumda duran"
echo "  kuralın ömrü, onu hatırlayan kişinin ömrü kadardır."
