# AGENTS.md

Bu depo, Beckhoff/TwinCAT odaklı fakat uzun vadede farklı PLC sistemlerine de uyarlanabilecek modüler bir **PLC Telemetry Platform** geliştirmek için kullanılacaktır.

Bu dosya, Codex ve benzeri kod ajanları için uygulama kurallarını, sınırları ve çalışma önceliklerini tanımlar.

---

## 1. Temel Amaç

Amaç yalnızca ekranlı bir logger üretmek değildir. Amaç şudur:

- PLC'den seçili verileri güvenilir şekilde toplamak
- ADS ve ileride UDP üzerinden bu verileri PC tarafına taşımak
- Verileri session mantığı ile kayıt altına almak
- Sonradan açıp analiz etmek
- Canlı debug ve grafikleme sağlamak
- Bütün sistemi tekrar kullanılabilir bir kütüphane / platform gibi tasarlamak

Bu nedenle proje, **GUI-first** değil, **core-first** yaklaşımıyla geliştirilmelidir.

---

## 2. Büyük Mimari İlkeler

Ajan aşağıdaki mimariyi korumalıdır:

```text
PLC Signal Source
  -> Registry / Publisher
  -> Transport Adapter (ADS / UDP)
  -> Collector / Normalizer
  -> Recorder / Storage
  -> Offline Viewer / Live GUI / Export
```

### Zorunlu ilkeler

1. **GUI çekirdekten bağımsız olmalı.**
2. **Transport katmanı soyutlanmalı.**
3. **Storage katmanı değiştirilebilir olmalı.**
4. **Signal metadata ve sample verisi birbirinden ayrılmalı.**
5. **Headless çalışma modu desteklenmeli.**
6. **İlk sürümde çalışan küçük çekirdek, yarım dev GUI'den daha değerlidir.**

---

## 3. Kesin Yasaklar

Ajan aşağıdaki hatalara düşmemelidir:

### 3.1 GUI ile başlama
İlk önemli teslim, canlı pencere değil; çalışan recorder çekirdeğidir.

### 3.2 Tek seferde dev framework kurma
İlk commitlerde plugin sistemi, dependency injection çılgınlığı, aşırı soyutlama, gereksiz enterprise mimari kurulmasın.

### 3.3 ADS'ye gömülme
İlk aşamada ADS kullanılabilir, ancak tasarım yalnızca ADS'ye kilitlenmemelidir. Kod tabanında `TransportAdapter` mantığı korunmalıdır.

### 3.4 CSV'yi tek native format yapmak
CSV yalnızca export formatı olmalıdır. Native kayıt formatı Parquet + metadata json yaklaşımıyla tasarlanmalıdır.

### 3.5 Session metadata'yı ihmal etmek
Her kayıt oturumu için manifest bilgisi zorunludur.

---

## 4. Geliştirme Öncelik Sırası

Ajan şu sırayı izlemelidir:

1. Domain modelleri
2. Config yükleme
3. Recorder/storage çekirdeği
4. ADS adapter
5. Headless CLI kayıt akışı
6. Offline viewer
7. Live viewer / GUI
8. UDP adapter
9. Gelişmiş replay / trigger / analiz

Bu sıra bozulmamalıdır; çok güçlü bir gerekçe olmadıkça GUI fazına erkenden atlanmamalıdır.

---

## 5. Kod Standartları

### 5.1 Dil ve isimlendirme
- Kod ve yorumlar İngilizce olmalı.
- Kullanıcıya dönük belge ve açıklamalar Türkçe olabilir.
- Dosya ve modül adları açık, sade ve kısa olmalı.

### 5.2 Python sürümü
- Python 3.11+ hedeflenmeli.

### 5.3 Tip kullanımı
- Yeni yazılan tüm çekirdek modüllerde type hints kullanılmalı.
- `dataclass` veya `pydantic` benzeri yapı yalnızca gerçekten faydalı ise tercih edilmeli.

### 5.4 Loglama
- `print` yerine `logging` tabanlı yapı tercih edilmeli.
- Kritik runtime olayları log seviyelerine ayrılmalı.

### 5.5 Hata yönetimi
- Sessizce yutulan exception olmamalı.
- Transport ve storage hataları açık biçimde raporlanmalı.

---

## 6. Proje Yapısı Beklentisi

Ajan aşağıdaki klasör yapısını korumalı veya buna yakın kalmalıdır:

```text
src/plc_telemetry/
  core/
    models/
    config/
    recorder/
    storage/
    services/
  transports/
    ads/
    udp/
  analysis/
  gui/
  utils/
tests/
docs/
examples/
scripts/
```

Ajan, tek dosyada devasa kod üretmemelidir. Modüller küçük ve sorumlulukları belirgin olmalıdır.

---

## 7. Domain Model Beklentileri

Ajan aşağıdaki kavramları açıkça modellemelidir:

- `SignalDefinition`
- `SignalType`
- `Sample`
- `SessionManifest`
- `TransportAdapter`
- `RecorderService`
- `SessionWriter`
- `SessionReader`

Minimum metadata alanları:

- channel_id
- name
- path
- data_type
- unit
- group
- enabled
- sample_mode
- sample_interval_ms

Minimum sample alanları:

- channel_id
- plc_timestamp_ns veya plc_timestamp_us
- pc_timestamp_ns
- value
- quality
- sequence_number (özellikle UDP tarafında)

---

## 8. Storage Kuralları

Native oturum yazımı için hedef yaklaşım:

- `session.json` -> metadata / manifest
- `samples.parquet` -> örnekler
- opsiyonel `events.jsonl` -> olaylar / notlar / markerlar

CSV yalnızca export çıktısıdır.

Ajan, storage tasarımını ileride aşağıdakilere açık bırakmalıdır:

- Parquet
- SQLite
- JSON Lines
- custom binary

Ama ilk çalışan sürümde Parquet hedeflenmelidir.

---

## 9. ADS ve UDP İçin Kurallar

### ADS
- İlk çalışan adapter olabilir.
- Değişken okuma basit ama test edilebilir modüller halinde yazılmalı.
- Beckhoff bağımlı kod yalnızca ilgili adapter klasöründe tutulmalı.

### UDP
- Sonradan eklenecek ama tasarım buna hazır olmalı.
- Paketlerde en az şu alanlar düşünülmeli:
  - schema_version
  - frame_type
  - sequence_number
  - plc_timestamp
  - payload_length
  - optional CRC

Endian, alignment ve packet parsing açıkça tanımlanmalıdır.

---

## 10. Test Beklentileri

Ajan yeni modül eklerken mümkünse test de eklemelidir.

Öncelikli test alanları:

- config parsing
- domain model validation
- session manifest serialization
- sample writing / reading
- path generation
- value normalization
- export logic

Transport adapter'lar için mümkün olduğunda fake/mock katmanlar kullanılmalıdır.

---

## 11. Başlangıçta Beklenen İlk Çıktılar

Ajan ilk dalgada aşağıdakileri üretmeye odaklanmalıdır:

1. Paket yapısı
2. Temel domain modelleri
3. YAML config loader
4. Session manifest modeli
5. Parquet writer iskeleti
6. Headless kayıt başlat/durdur akışı
7. Basit CLI giriş noktası

Canlı GUI ikinci dalga işidir.

---

## 12. Commit Disiplini

Ajanın ürettiği değişiklikler mümkün olduğunca küçük ve anlamlı parçalara bölünmelidir.

Önerilen commit mantığı:

- `feat(core): add signal definition model`
- `feat(storage): add parquet session writer`
- `feat(config): add yaml config loader`
- `feat(cli): add headless record command`
- `test(core): add signal model tests`

Büyük ve karmakarışık tek commit tercih edilmemelidir.

---

## 13. Karar Verirken Referans Alınacak Kural

Bir tasarım tercihi arasında kalındığında şu soru sorulmalıdır:

> Bu karar, sistemi tekrar kullanılabilir ve GUI'den bağımsız bir telemetry platformuna yaklaştırıyor mu, yoksa tek projelik dağınık bir logger'a mı dönüştürüyor?

İkinci seçeneğe götürüyorsa tercih edilmemelidir.
