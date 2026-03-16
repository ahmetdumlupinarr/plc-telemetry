# PLC Telemetry Platform — Master Plan

## Belge Amacı

Bu belge, Beckhoff/TwinCAT odaklı fakat uzun vadede farklı PLC ve gömülü sistemlere de uyarlanabilecek **genel amaçlı bir telemetry / logger / debug platformunun** teknik kapsamını, mimarisini, faz planını ve geliştirme önceliklerini tanımlar.

Belge, özellikle aşağıdaki amaçlarla hazırlanmıştır:

- Codex ve benzeri ajanların geliştirme sırasında referans alacağı tekil kaynak olmak
- Projenin kapsam kaymasını engellemek
- GUI, transport ve kayıt mekanizmalarını birbirinden ayıran sürdürülebilir bir mimari kurmak
- MVP ile ileri seviye sürümler arasındaki yolu netleştirmek
- PLC tarafı ile Python tarafının sorumluluklarını açık biçimde ayırmak

---

# 1. Proje Tanımı

## 1.1 Kısa Tanım

Bu proje, PLC tarafında tanımlanan seçili değişkenlerin ADS veya UDP üzerinden bilgisayara aktarılması; bilgisayar tarafında ise bu verilerin:

- toplanması,
- zaman damgalanması,
- kaydedilmesi,
- canlı debug olarak gösterilmesi,
- grafiklenmesi,
- dışa aktarılması,
- oturum bazlı arşivlenmesi

amacıyla geliştirilecek modüler bir Python uygulamasıdır.

## 1.2 Vizyon

Bu yazılım yalnızca bir “ekranlı logger” değildir. Uzun vadede hedef, tekrar kullanılabilir bir **PLC Telemetry Platform** oluşturmaktır.

Bu platform aşağıdaki rolleri üstlenebilmelidir:

- canlı izleme aracı,
- veri kayıt motoru,
- oturum bazlı inceleme aracı,
- debug yardımcı aracı,
- saha testlerinde raporlama altyapısı,
- motion/control sistemleri için analiz platformu.

## 1.3 Temel İlke

> Önce veri hattı ve kayıt motoru kurulur. GUI sonradan eklenir.

Yanlış yaklaşım: doğrudan tam özellikli GUI ile başlamak.

Doğru yaklaşım:

1. veri modeli,
2. transport adapter,
3. collector / recorder,
4. storage,
5. offline viewer,
6. canlı GUI,
7. ileri analiz özellikleri.

---

# 2. Kapsam

## 2.1 İn-Scope

Aşağıdaki konular bu projenin kapsamındadır:

- PLC’den seçilmiş değişkenlerin alınması
- ADS adapter
- UDP adapter
- Canlı veri toplama
- Dosyaya kayıt alma
- Session/oturum mantığı
- Kanal metadata yönetimi
- Sayısal, boolean ve enum-benzeri verilerin gösterimi
- Grafikleme
- Dışa aktarma (özellikle CSV, PNG, JSON; tercihen Parquet tabanlı native kayıt)
- Basit ama sürdürülebilir desktop GUI
- PLC tarafında standart bir logger publisher yapısı oluşturulması
- Genişletilebilir modüler Python mimarisi

## 2.2 Out-of-Scope (ilk sürüm için)

Aşağıdaki konular ilk sürümde zorunlu değildir:

- Bulut senkronizasyonu
- Multi-user web dashboard
- Veritabanı sunucusu tabanlı merkezi telemetri altyapısı
- Gelişmiş alarm yönetim sistemi
- FFT / frekans analizi
- Makine öğrenmesi temelli anomali tespiti
- PLC tarafında otomatik reflection / symbol parser jenerasyonu
- Tam kapsamlı report designer
- OPC UA / MQTT desteği (ilk sürümde değil, ileri fazda)

---

# 3. Hedefler ve Başarı Kriterleri

## 3.1 Fonksiyonel Hedefler

Sistem şu işleri yapabilmelidir:

1. Tanımlı sinyal listesini okuyabilmek
2. Bu sinyalleri belirli örnekleme mantığı ile toplayabilmek
3. Gelen verileri oturum bazlı kayıt altına alabilmek
4. Daha sonra aynı oturumu açıp inceleyebilmek
5. Canlı durumda en az temel debug ekranı sağlayabilmek
6. Verileri taşınabilir biçimde dışa aktarabilmek

## 3.2 Mühendislik Hedefleri

- Taşınabilir kod yapısı
- Katmanlı mimari
- Test edilebilir modüller
- GUI ile çekirdek mantığın ayrılması
- Transport katmanının soyutlanması
- Dosya formatının uzun vadede bozulmadan genişleyebilmesi

## 3.3 Başarı Kriterleri

MVP başarılı sayılır, eğer:

- ADS üzerinden en az 20–50 kanal güvenilir biçimde okunabiliyorsa
- Kayıtlar session mantığında dosyaya alınabiliyorsa
- Session metadata saklanabiliyorsa
- Kayıtlı veri tekrar açılabiliyorsa
- En az temel grafik ve export alınabiliyorsa

---

# 4. Kullanım Senaryoları

## 4.1 Motion Debug

Kullanıcı bir eksen veya anten sistemi üzerinde aşağıdaki sinyalleri canlı izlemek ister:

- ActPos
- SetPos
- ActVel
- SetVel
- FollowingError
- Torque
- Enable
- Error
- LimitSwitch

Aynı zamanda test süresince bunları kayıt altına alıp daha sonra grafik üzerinde incelemek ister.

## 4.2 Fault Snapshot

Sahada bir hata oluştuğunda, olaydan hemen önceki ve sonraki süreç incelenmek istenir.

## 4.3 Genel Amaçlı Debug

Kullanıcı belirli GVL / FB / PRG değişkenlerini seçip canlı true/false ve sayısal değerlerini görmek ister.

## 4.4 Test Raporlama

Belirli bir test koşulunda alınan veriler daha sonra dışa aktarılıp rapora dönüştürülmek istenir.

---

# 5. Üst Seviye Mimari

Aşağıdaki veri akışı hedeflenmektedir:

```text
PLC Signal Source
    -> Signal Registry / Publisher
    -> Transport Layer (ADS / UDP)
    -> PC Collector
    -> Recorder / Storage
    -> Offline Viewer / Live GUI / Export
```

## 5.1 Katmanlar

### Katman 1 — Signal Definition / Registry

PLC tarafında hangi verilerin yayınlanacağı burada tanımlanır.

### Katman 2 — Transport Layer

Veri PC tarafına ADS veya UDP ile taşınır.

### Katman 3 — Collector / Normalizer

PC tarafında veriler toplanır, timestamp eklenir, kalite durumu belirlenir.

### Katman 4 — Recorder / Storage

Veriler oturum halinde diske kaydedilir.

### Katman 5 — Viewer / GUI / Export

Veriler canlı veya kayıtlı olarak kullanıcıya sunulur.

---

# 6. Mimari İlkeler

## 6.1 GUI çekirdekten bağımsız olmalı

Recorder, collector ve transport kodları GUI olmadan da çalışmalıdır.

## 6.2 Transport soyut olmalı

Kod, ADS’ye kilitli kalmamalıdır. ADS ilk sürüm için kullanılabilir; ancak UDP ikinci adapter olarak planlanmalıdır.

## 6.3 Kanal tanımı metadata ile birlikte tutulmalı

Bir sinyal yalnızca “değer” değildir. Şu bilgiler de saklanmalıdır:

- isim
- tip
- birim
- grup
- açıklama
- display hint
- örnekleme modu

## 6.4 Session bazlı düşünülmeli

Her kayıt bir oturum olarak ele alınmalıdır. Her session şu bilgileri taşımalıdır:

- session_id
- başlangıç / bitiş zamanı
- transport tipi
- logged channels
- uygulama sürümü
- schema version
- kullanıcı notu (opsiyonel)

## 6.5 Veri formatı genişletilebilir olmalı

İleride yeni kanal tipleri, enum map’leri, quality alanları ve derived signals eklenebilmeli.

---

# 7. PLC Tarafı Tasarım İlkeleri

## 7.1 Amaç

PLC tarafında loglanacak sinyalleri dağınık biçimde okumak yerine, tek bir merkezi yapı ile tanımlamak.

## 7.2 Önerilen PLC Yapısı

```text
PLC_Logger/
├─ GVL_Logger
├─ GVL_LoggerConfig
├─ DUT/
│  ├─ ST_LogChannel
│  ├─ ST_LogValue
│  ├─ ST_LogFrameHeader
│  └─ ST_LogFrameMeta
├─ FB/
│  ├─ FB_LoggerRegistry
│  ├─ FB_LoggerPublisherAds
│  └─ FB_LoggerPublisherUdp
└─ PRG_LoggerDemo
```

## 7.3 Kanal Tanımı

Her log kanalı için en az şu alanlar bulunmalıdır:

- `ChannelId : UINT`
- `Name : STRING`
- `Type : E_LogValueType`
- `Unit : STRING`
- `Group : STRING`
- `Enabled : BOOL`
- `SampleMode : E_LogSampleMode`
- `Deadband : LREAL`
- `DisplayHint : E_LogDisplayHint`

## 7.4 Örnekleme Modları

En az aşağıdaki modlar hedeflenmelidir:

- cyclic every N ms
- on change
- triggered snapshot

İlk sürümde sadece cyclic yeterlidir; tasarım buna göre ileride genişletilebilmelidir.

## 7.5 PLC Tarafı Yaklaşım Kararı

### Seçenek A — PC, ADS ile değişkenleri doğrudan isimden okur
Artı: çok hızlı MVP.
Eksi: namespace değişince kırılganlık, metadata eksikliği, senkron toplama zorluğu.

### Seçenek B — PLC içinde logger publisher katmanı kurulur
Artı: standart veri modeli, transport bağımsız tasarım, daha profesyonel yapı.
Eksi: ilk kurulum maliyeti daha fazla.

**Karar:**
- Faz 1’de ADS ile hızlı başlangıç yapılabilir.
- Ancak PLC publisher standardı proje planına erken dahil edilmelidir.

---

# 8. PC Tarafı Mimari

## 8.1 Ana Modüller

### `core.models`
Temel veri sınıfları.

### `core.config`
YAML ve diğer konfigürasyonların okunması.

### `transports.ads`
ADS collector / adapter.

### `transports.udp`
UDP listener / parser.

### `core.recorder`
Session yönetimi ve kayıt motoru.

### `core.storage`
Parquet / metadata / export katmanı.

### `analysis`
Kayıtlı dosya yükleme ve offline analiz.

### `gui`
Canlı veya offline kullanıcı arayüzü.

---

# 9. Python Proje Yapısı

```text
plc_telemetry_platform/
├─ app/
│  ├─ main.py
│  ├─ cli.py
│  └─ bootstrap.py
├─ core/
│  ├─ models/
│  │  ├─ signal_definition.py
│  │  ├─ sample.py
│  │  ├─ session_manifest.py
│  │  └─ enums.py
│  ├─ config/
│  │  ├─ loader.py
│  │  └─ schema.py
│  ├─ recorder/
│  │  ├─ recorder_service.py
│  │  ├─ session_service.py
│  │  └─ ring_buffer.py
│  ├─ storage/
│  │  ├─ parquet_writer.py
│  │  ├─ manifest_writer.py
│  │  ├─ session_loader.py
│  │  └─ exporters.py
│  └─ services/
│     ├─ sampling_service.py
│     └─ replay_service.py
├─ transports/
│  ├─ base/
│  │  └─ adapter.py
│  ├─ ads/
│  │  ├─ ads_adapter.py
│  │  └─ symbol_reader.py
│  └─ udp/
│     ├─ udp_adapter.py
│     ├─ packet_parser.py
│     └─ schema_registry.py
├─ gui/
│  ├─ app.py
│  ├─ widgets/
│  ├─ views/
│  ├─ viewmodels/
│  └─ resources/
├─ analysis/
│  ├─ session_analysis.py
│  ├─ plotting.py
│  └─ metrics.py
├─ protocols/
│  ├─ udp/
│  │  ├─ frame_definitions.md
│  │  └─ packet_examples.json
│  └─ schemas/
├─ tests/
├─ examples/
├─ docs/
└─ scripts/
```

---

# 10. Teknoloji Tercihleri

## 10.1 GUI

**Öneri:** `PySide6 + pyqtgraph`

Gerekçe:

- gerçek zamanlı grafik için uygun
- masaüstü uygulaması için daha güçlü
- debug panel / dock / tablo / split görünüm daha rahat
- performans açısından canlı data ekranları için Streamlit’ten daha uygun

## 10.2 Veri İşleme

- `polars` veya `pandas`
- offline analiz ve export için kullanılacak

## 10.3 Kayıt Formatı

**Native format:** `Parquet + session.json`

Gerekçe:

- CSV’ye göre tip ve performans avantajı
- büyük veri için uygun
- pandas/polars ile güçlü uyum
- export için CSV ayrıca üretilebilir

## 10.4 Konfigürasyon

**Öneri:** `YAML`

## 10.5 Paketleme

- Python 3.11+ önerilir
- `uv` veya `poetry` değerlendirilebilir
- build/package ileri aşamada düşünülür

---

# 11. Veri Modeli

## 11.1 SignalDefinition

Bir kanalın sabit metadata’sını tanımlar.

Örnek alanlar:

- `channel_id: int`
- `name: str`
- `path: str`
- `value_type: str`
- `unit: str | None`
- `group: str | None`
- `description: str | None`
- `display_hint: str`
- `sample_mode: str`
- `enabled: bool`

## 11.2 Sample

Tek bir örnek veri kaydı.

Örnek alanlar:

- `session_id: str`
- `timestamp_plc_ns: int | None`
- `timestamp_pc_ns: int`
- `channel_id: int`
- `value_numeric: float | None`
- `value_bool: bool | None`
- `value_text: str | None`
- `quality: str`
- `sequence_no: int | None`

## 11.3 SessionManifest

Bir kayıt oturumunun metadata’sı.

Örnek alanlar:

- `session_id`
- `project_name`
- `plc_name`
- `transport`
- `schema_version`
- `app_version`
- `start_time`
- `end_time`
- `channel_count`
- `logged_channels`
- `notes`

## 11.4 Quality Alanı

İleri seviye debugging için şu kalite durumları desteklenebilir:

- `good`
- `stale`
- `timeout`
- `invalid`
- `dropped`
- `extrapolated`

---

# 12. Transport Katmanı

## 12.1 Ortak Arabirim

Transport katmanı ortak bir adapter arabirimi ile soyutlanmalıdır.

Örnek sorumluluklar:

- bağlantı açma
- bağlantı kapama
- sinyal listesi ile toplama başlatma
- veri callback / queue üretme
- durum bilgisi sağlama

## 12.2 ADS Adapter

İlk MVP’nin ana taşıyıcısı.

Sorumluluklar:

- AMS Net ID / port ile bağlantı kurmak
- tanımlı sembolleri okumak
- periyodik polling yapmak
- okunan verileri normalize edip sample üretmek

Not:
ADS ilk MVP için pratik olsa da mimari ADS’ye kilitlenmemelidir.

## 12.3 UDP Adapter

İleri fazda eklenecek ikinci ana adapter.

Sorumluluklar:

- UDP socket dinlemek
- frame parse etmek
- sequence/CRC/version kontrolü yapmak
- payload’u sample’lara dönüştürmek

---

# 13. UDP Çerçeve Taslağı

İlk taslak olarak aşağıdaki alanlar önerilir:

## 13.1 Frame Header

- `Magic` : 2 byte
- `Version` : 1 byte
- `HeaderSize` : 1 byte
- `FrameType` : 1 byte
- `Flags` : 1 byte
- `SequenceNo` : 4 byte
- `TimestampPlcNs` : 8 byte
- `ChannelCount` : 2 byte
- `PayloadSize` : 2 byte
- `Crc32` : 4 byte

## 13.2 Channel Payload Entry

- `ChannelId` : 2 byte
- `ValueType` : 1 byte
- `Quality` : 1 byte
- `ValueLength` : 2 byte
- `ValueBytes` : variable

## 13.3 Gerekli Özellikler

- versioning
- endian kararı net olmalı
- CRC olmalı
- sequence number olmalı
- timestamp olmalı

## 13.4 İlkeler

- Paket formatı dökümante edilmeli
- Örnek frame’ler JSON/binary örneklerle `protocols/` altında tutulmalı
- PLC ve Python tarafı tek kaynaktan aynı protokolü referans almalı

---

# 14. Storage Katmanı

## 14.1 Native Session Saklama

Her oturum için aşağıdaki yapı önerilir:

```text
sessions/
└─ 2026-03-16_azimuth_test_001/
   ├─ session.json
   ├─ samples.parquet
   ├─ channels.json
   ├─ events.json
   └─ notes.txt
```

## 14.2 Session Dosyaları

### `session.json`
Session manifest ve genel metadata.

### `samples.parquet`
Asıl örnek veriler.

### `channels.json`
Kanal listesi ve metadata.

### `events.json`
Alarm, trigger, not gibi olaylar için rezerv alan.

## 14.3 Export Formatları

- CSV
- JSON
- Excel (ileri faz)
- PNG grafik
- session zip paketi

---

# 15. GUI Tasarım Prensipleri

## 15.1 Amaç

GUI çekirdek mantığın üzerine takılan bir arayüz katmanı olmalıdır; uygulamanın omurgası GUI’ye bağlı olmamalıdır.

## 15.2 Ana Ekranlar

### Live Dashboard

- bağlantı durumu
- aktif session durumu
- örnekleme hızı
- queue/backlog istatistikleri
- drop sayacı
- son değerler

### Debug Panel

- değişken listesi
- true/false renkli gösterim
- sayısal değerler
- min/max
- son güncelleme zamanı

### Plot View

- çoklu kanal seçimi
- zoom/pan
- cursor
- kanal gizleme/gösterme

### Session Browser

- kayıtlı session’ları listeleme
- metadata görüntüleme
- oturum açma

### Export Panel

- session export
- kanal bazlı export
- görüntü export

## 15.3 Tasarım İlkeleri

- önce işlev, sonra görsel cilalama
- düşük sürtünmeli kullanım
- motion/debug odaklı düzen
- büyük veri ile çalışırken UI kilitlenmemeli

---

# 16. Faz Planı

## Faz 0 — Tasarım ve İskele

### Hedef
Kapsam, mimari ve temel iskeleti netleştirmek.

### Çıktılar
- bu master belge
- repo iskeleti
- temel veri modelleri
- config taslağı
- backlog listesi

### Kabul Kriteri
- klasör yapısı oluşmuş olmalı
- temel modüller isimlendirilmiş olmalı
- teknoloji seçimleri netleşmiş olmalı

---

## Faz 1 — Headless Logger MVP

### Hedef
GUI olmadan çalışan temel veri toplama ve kayıt sistemi.

### Özellikler
- YAML config okuma
- ADS adapter ile veri toplama
- session başlatma / durdurma
- Parquet kayıt alma
- session.json üretme
- terminal tabanlı durum çıktısı
- temel export komutları

### Teslimler
- CLI komutları
- örnek config
- örnek session kaydı
- temel testler

### Kabul Kriteri
- ADS üzerinden seçili kanallar okunabiliyor olmalı
- session kaydı güvenilir olmalı
- kayıtlı veri yeniden açılabiliyor olmalı

---

## Faz 2 — Offline Viewer

### Hedef
Kayıtlı session’ların grafiklenip incelenebilmesi.

### Özellikler
- session açma
- kanal seçme
- grafik gösterme
- bool / numeric ayrımı
- CSV export
- PNG export

### Kabul Kriteri
- en az bir kayıtlı session açılıp incelenebilmeli
- grafikler düzgün çizilebilmeli

---

## Faz 3 — PLC Publisher Standardı

### Hedef
PLC tarafında loggable veri için standart registry/publisher yapısı kurmak.

### Özellikler
- `ST_LogChannel`
- `FB_LoggerRegistry`
- channel metadata
- ileride UDP’ye hazır çerçeve

### Kabul Kriteri
- PLC tarafında log kanalları merkezi yapıdan tanımlanabilmeli

---

## Faz 4 — Live GUI

### Hedef
Canlı debug ve temel canlı plot desteği eklemek.

### Özellikler
- live dashboard
- debug table
- canlı plot
- connection status
- session recording controls

### Kabul Kriteri
- canlı veri akışı GUI’de görüntülenebilmeli
- GUI, veri akışını bloklamamalı

---

## Faz 5 — UDP Adapter

### Hedef
Standart UDP publisher ve UDP collector desteği eklemek.

### Özellikler
- UDP frame parser
- sequence kontrolü
- CRC kontrolü
- timestamp ve schema version doğrulama

### Kabul Kriteri
- PLC’den UDP ile gelen veri kaydedilebilmeli ve izlenebilmeli

---

## Faz 6 — Gelişmiş Özellikler

### Örnekler
- trigger recording
- pre/post trigger buffer
- replay mode
- compare sessions
- derived channels
- hazır motion template ekranları
- alarm/event marker

---

# 17. MVP Tanımı

İlk gerçek ürün sürümü şu kapsamda hedeflenir:

## PLC Tarafı
- ADS ile erişilebilir kanal listesi
- tercihen sabit örnek signal set

## Python Tarafı
- YAML config
- ADS collector
- Parquet recorder
- session metadata
- offline viewer
- CSV export

Bu aşamada full canlı GUI zorunlu değildir.

---

# 18. Önerilen Config Yapısı

Aşağıdaki yapı taslak niteliğindedir:

```yaml
project:
  name: antenna_motion_logger
  description: Azimuth/Elevation telemetry recording
  storage_root: ./sessions

transport:
  type: ads
  ads:
    ams_net_id: "127.0.0.1.1.1"
    port: 851
    poll_interval_ms: 10

session:
  name_prefix: azimuth_test
  auto_start: false
  manifest_notes: "Initial telemetry test"

channels:
  - channel_id: 1
    name: ActPos
    path: GVL.axAzimuth_ActPos
    value_type: lreal
    unit: deg
    group: motion
    display_hint: plot
    enabled: true

  - channel_id: 2
    name: SetPos
    path: GVL.axAzimuth_SetPos
    value_type: lreal
    unit: deg
    group: motion
    display_hint: plot
    enabled: true

  - channel_id: 3
    name: AxisReady
    path: GVL.xAxisReady
    value_type: bool
    unit: null
    group: status
    display_hint: bool
    enabled: true
```

---

# 19. Önerilen Temel Sınıflar

## 19.1 `SignalDefinition`
Kanal metadata modeli.

## 19.2 `Sample`
Tekil veri örneği.

## 19.3 `TransportAdapter`
Tüm transport tiplerinin uyması gereken soyut arayüz.

## 19.4 `AdsAdapter`
ADS veri sağlayıcısı.

## 19.5 `UdpAdapter`
UDP veri sağlayıcısı.

## 19.6 `RecorderService`
Veri kuyruğundan alıp session dosyalarına yazar.

## 19.7 `SessionService`
Session başlatma / bitirme / metadata yönetimi.

## 19.8 `SessionLoader`
Kayıtlı oturumları açar.

## 19.9 `ExportService`
CSV / JSON / PNG export üretir.

## 19.10 `ReplayService`
İleri faz için session replay işlevi sağlar.

---

# 20. Test Stratejisi

## 20.1 Unit Test

- config parsing
- metadata validation
- sample normalization
- parquet yazma/okuma
- UDP frame parsing
- quality flag mantığı

## 20.2 Integration Test

- ADS adapter ile gerçek veya simüle veri akışı
- UDP adapter ile frame acceptance test
- session lifecycle test

## 20.3 Manual Test

- motion sinyallerinin canlı gözlemi
- uzun süreli kayıt testi
- yüksek frekans veri akışı altında davranış
- export doğrulama

---

# 21. Performans ve Dayanıklılık Konuları

## 21.1 Thread Ayrımı

Canlı GUI aşamasında en az şu ayrım düşünülmelidir:

- acquisition thread
- recorder thread
- UI thread

## 21.2 Kuyruk Yönetimi

Aşırı veri akışında sistemin davranışı kontrollü olmalıdır.

Öneriler:

- bounded queue
- backlog metriği
- drop counter
- warning mekanizması

## 21.3 Zaman Damgası

Mümkünse hem:

- PLC timestamp
- PC receive timestamp

saklanmalıdır.

## 21.4 Veri Büyümesi

Uzun kayıtlar için Parquet tercih edilmeli; CSV yalnızca export amacıyla kullanılmalıdır.

---

# 22. Riskler ve Önlemler

## Risk 1 — GUI’ye çok erken girilmesi
Sonuç: veri hattı oturmadan arayüz işlerine boğulma.

**Önlem:** Faz 1 ve Faz 2 bitmeden kapsamlı live GUI’ye girme.

## Risk 2 — ADS’ye aşırı bağımlı kalmak
Sonuç: sistem genelleşemez.

**Önlem:** adapter tabanı ve UDP planı baştan belgelenmiş olmalı.

## Risk 3 — CSV merkezli tasarım
Sonuç: performans, tip güvenliği ve ölçeklenebilirlik sorunları.

**Önlem:** native format olarak Parquet kullan.

## Risk 4 — Metadata eksikliği
Sonuç: daha sonra hangi sinyalin ne olduğu unutulur.

**Önlem:** channel metadata zorunlu alanlarla tutulmalı.

## Risk 5 — Protokol sürümlemesinin ihmal edilmesi
Sonuç: UDP tarafında kırılganlık.

**Önlem:** `schema_version`, `frame_version`, `sequence_no`, `crc` tasarıma erken dahil edilmeli.

---

# 23. Kodlama Standartları

## 23.1 Genel

- modüler yaz
- tek sorumluluk ilkesine uy
- GUI kodu ile iş mantığını ayır
- sabitleri merkezi yerde tut
- type hints kullan
- test edilebilir fonksiyonlar yaz

## 23.2 İsimlendirme

- Python modülleri: `snake_case`
- sınıflar: `PascalCase`
- sabitler: `UPPER_SNAKE_CASE`
- session ve dosya isimleri: okunabilir ve zaman damgalı

## 23.3 Dokümantasyon

- her ana modül için kısa README
- transport protokolleri için örnek veri
- config formatı için açıklama

---

# 24. İlk Backlog Önerisi

## Epic A — Core Models
- [ ] enums tanımları
- [ ] SignalDefinition modeli
- [ ] Sample modeli
- [ ] SessionManifest modeli

## Epic B — Config
- [ ] YAML loader
- [ ] config validation
- [ ] örnek config dosyası

## Epic C — Storage
- [ ] session folder oluşturma
- [ ] session.json yazma
- [ ] channels.json yazma
- [ ] parquet writer
- [ ] parquet reader

## Epic D — ADS Adapter
- [ ] connection wrapper
- [ ] symbol read abstraction
- [ ] polling loop
- [ ] sample normalize etme

## Epic E — CLI
- [ ] start session
- [ ] stop session
- [ ] list sessions
- [ ] export session

## Epic F — Offline Viewer
- [ ] session browser
- [ ] channel selector
- [ ] plot rendering
- [ ] bool/numeric render ayrımı

## Epic G — PLC Standardı
- [ ] ST_LogChannel tasarımı
- [ ] logger registry yapısı
- [ ] publisher taslağı

## Epic H — UDP
- [ ] frame spec dokümanı
- [ ] parser skeleton
- [ ] test packet örnekleri

---

# 25. Codex / Ajan Çalışma Kuralları

Bu proje üzerinde çalışan ajanlar aşağıdaki ilkelere uymalıdır:

1. GUI’den önce core ve storage katmanı yazılmalı
2. ADS adapter, `TransportAdapter` tabanını ihlal etmemeli
3. CSV merkezli tasarım yapılmamalı
4. Session manifest zorunlu kabul edilmeli
5. Kod örnekleri MVP ile ileri seviye özellikleri karıştırmamalı
6. Her ana modül için en az temel test iskeleti oluşturulmalı
7. Tasarım kararlarını dosya içinde küçük notlarla açıklamak tercih edilmeli

Ek olarak ajanlardan beklenen yaklaşım:

- önce iskelet,
- sonra çalışan minimal akış,
- sonra refactor,
- en son GUI genişlemesi.

---

# 26. İlk Teslim Paketi İçin Beklenenler

Aşağıdaki çıktılar ilk anlamlı teslim paketi için yeterli kabul edilir:

- repo iskeleti
- temel veri modelleri
- YAML config loader
- ADS tabanlı minimal collector
- session kayıt mantığı
- Parquet writer
- session.json üretimi
- örnek config
- örnek session output
- kısa kullanım README

---

# 27. Orta Vadeli Genişleme Alanları

İleri sürümlerde aşağıdakiler değerlendirilebilir:

- trigger bazlı kayıt
- pre/post event buffer
- derived channel formülleri
- hazır motion dashboard şablonları
- error/fault timeline
- replay mode
- compare sessions
- plugin bazlı transport desteği
- OPC UA adapter
- MQTT adapter

---

# 28. Sonuç

Bu projenin doğru formu “tek seferlik bir logger GUI” değil, modüler ve genişleyebilir bir **PLC Telemetry Platform** olmaktır.

Doğru ilerleme sırası şudur:

1. veri modeli,
2. config,
3. transport abstraction,
4. recorder ve storage,
5. CLI ile çalışan headless MVP,
6. offline viewer,
7. PLC publisher standardı,
8. canlı GUI,
9. UDP ve ileri seviye özellikler.

Bu sıraya uyulursa proje kısa vadede iş gören, uzun vadede ise tekrar kullanılabilir bir mühendislik altyapısına dönüşür.

