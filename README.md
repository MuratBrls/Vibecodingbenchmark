# ⚡ VibeBench — Multi-AI Coding Benchmark (v2.2-local)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)]()
[![Status](https://img.shields.io/badge/Status-Active-brightgreen)]()

**Black Box Deep Analytics Tool** for measuring AI coding performance in real-time.
Designed for local, on-premise benchmarking with **zero network latency** and **highest precision**.

---

## 🌟 Neden VibeBench?

Geleneksel kodlama benchmarkları genellikle sadece "kod çalışıyor mu?" sorusuna odaklanır. VibeBench ise yapay zekanın **nasıl düşündüğünü** ve **nasıl kodladığını** derinlemesine analiz eder.

### Temel Felsefe:
1.  **Gerçek Zamanlılık:** AI'nın düşünme süresi ile kod yazma süresini milisaniye hassasiyetinde ayırır.
2.  **Lokal On-Premise:** Ağ gecikmelerini elimine eder. Tüm süreç yerel disk ve CPU/RAM üzerinde döner.
3.  **Çok Boyutlu Analiz:** Sadece hız değil; mimari kalite, temiz kod prensipleri ve kaynak verimliliği de puanlanır.

---

## 🏗️ Mimari ve Teknoloji (v2.2-local)

VibeBench v2.2, tamamen lokalize edilmiş bir motor kullanır:

*   **⏱️ Ms Hassasiyetinde Zamanlama (`perf_counter`):**
    *   Python'un en hassas zaman sayacı `time.perf_counter()` kullanılır.
    *   **Watchdog Polling:** Dosya sistemi değişiklikleri her **100ms**'de bir taranır (`SIGNAL_POLL_INTERVAL_MS`).
    *   Bu sayede AI'nın reaksiyon süresi (thinking time) hatasız ölçülür.

*   **🖥️ Anlık Kaynak Takibi (`psutil`):**
    *   Arka planda çalışan bir **Daemon Thread**, her **1.0 saniyede** bir sistem kaynaklarını örnekler.
    *   **CPU:** Anlık yük yüzdesi.
    *   **RAM:** Kullanılan bellek miktarı (MB).
    *   Bu veriler final skora etki etmese de raporlarda sunulur.

*   **🛡️ LocalErrorLogger (Dayanıklılık):**
    *   Windows dosya sistemi kısıtlamalarına (260 karakter, dosya kilitleme, izin sorunları) karşı özel bir koruma katmanı.
    *   Tüm I/O işlemleri `safe_write` wrapper'ı ile korunur.
    *   Hatalar `logs/local_errors.json` dosyasına ayrıntılı olarak işlenir.

---

## 📦 Kurulum

### Gereksinimler
*   Python 3.8 veya üzeri
*   Windows, Linux veya macOS (Windows önerilir)

### Adımlar

1.  **Projeyi Klonlayın:**
    ```powershell
    git clone https://github.com/MuratBrls/Vibecodingbenchmark.git
    cd Vibecodingbenchmark
    ```

2.  **Sanal Ortam (Opsiyonel ama Önerilir):**
    ```powershell
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Bağımlılıkları Yükleyin:**
    ```powershell
    pip install -r requirements.txt
    ```
    *(Temel paketler: `psutil`, `watchdog`, `rich`, `mccabe`, `pycodestyle`)*

---

## 🎮 Kullanım

### 1. Benchmark Başlatma (RUN)
En temel kullanım. Sisteme bir prompt verirsiniz ve izleme başlar.

```powershell
python main.py run "Bana OOP tabanlı bir hesap makinesi yap, loglama da olsun."
```

**Seçenekler:**
*   `--no-clean`: Önceki test dosyalarını silmeden çalıştırır. (Debug için yararlıdır)
*   `--timeout N`: Varsayılan 600 saniye olan zaman aşımını değiştirir.

### 2. Durum Kontrolü (STATUS)
Mevcut çalışan agent'ların durumunu, son raporu ve kaynak kullanımını gösterir.

```powershell
python main.py status
```

---

## 🤖 Vibe Protokolü (AI Agent'lar İçin)

Benchmark'a katılan her AI (Cursor, Windsurf, Antigravity vb.) aşağıdaki akışı **kesinlikle** uygulamalıdır:

1.  **🚀 BAŞLANGIÇ (Sinyal):**
    *   Çalışma klasörüne (`test-bench*`) `start_signal.json` adında boş bir dosya oluşturur.
    *   *Bu an, "Thinking Time"ın bittiği ve "Writing Time"ın başladığı andır.*

2.  **code KODLAMA:**
    *   İstenen kod dosyasını (örn: `calculator.py`) yazar ve kaydeder.
    *   *Dosyanın diske yazıldığı an "Writing Time" olarak kaydedilir.*

3.  **🏁 BİTİŞ (Sinyal):**
    *   İşlem tamamlanınca `start_signal.json` dosyasını siler.
    *   *Bu, görevin başarıyla tamamlandığını sisteme bildirir.*

---

## 📊 Puanlama Sistemi (Total Score)

VibeBench, 4 ana kategoride puanlama yapar. Toplam Puan 100 üzerinden hesaplanır.

### 1. ⏱️ Hız (Ağırlık: %30)
*   **Thinking Time:** Sinyal dosyası oluşana kadar geçen süre.
*   **Writing Time:** Kodun diske yazılmasına kadar geçen süre.
*   *Daha hızlı olan daha yüksek puan alır.*

### 2. 🏛️ Mimari & Kalite (Ağırlık: %30)
*   **Mimari Tipi:**
    *   `OOP` (Sınıf tabanlı) -> **100 Puan**
    *   `Functional` (Fonksiyonel) -> **80 Puan**
    *   `Scripting` (Düz kod) -> **40 Puan**
*   **McCabe Karmaşıklığı:** Kodun okunabilirliği ve bakımı (düşük olması iyidir).
*   **PEP8 Uyumu:** Python standartlarına uygunluk.
*   **Temiz Kod:** Fonksiyon/Sınıf oranları, docstring kullanımı.

### 3. ❌ Hata & Dayanıklılık (Ağırlık: %25)
*   **Syntax/Runtime Hatası:** Kodu çalıştırılamazsa 0 puan.
*   **Hata Oranı:** Her `SyntaxError` veya çalışma zamanı hatası **-10 puan** ceza getirir.
*   **Retry Sayısı:** AI kodu kaç kere düzeltip tekrar denedi? Her deneme puan düşürür.

### 4. 💎 Kütüphane Verimliliği (Ağırlık: %15)
*   **Gereksiz Import:** Kullanılmayan kütüphaneler puan düşürür.
*   **Standart Kütüphane:** Harici bağımlılık yerine standart kütüphane (os, sys, math) kullanımı teşvik edilir.

---

## 📁 Proje Yapısı

```
VibeCodingBenchmark/
├── main.py                # 🚀 CLI Giriş Noktası
├── config.py              # ⚙️ Ayarlar (Dizinler, Timeout, Polling)
├── watcher.py             # 👀 Dosya İzleme Motoru (Watchdog)
├── telemetry.py           # 📊 Kaynak Takibi (psutil)
├── scorer.py              # 🧮 Puanlama Algoritması
├── dashboard.py           # 🖥️ Terminal Arayüzü (Rich)
├── bench_logger.py        # 📝 Raporlama (JSON/HTML)
├── local_error_logger.py  # 🛡️ Hata Yönetimi
├── requirements.txt       # 📦 Bağımlılıklar
├── logs/                  # 📂 Rapor Çıktıları
└── test-bench*/           # 📂 AI Çalışma Alanları
```

---

## 🛡️ Sorun Giderme (Troubleshooting)

*   **`PermissionError` Hatası:**
    *   Yönetici olarak çalıştırmayı deneyin.
    *   Antivirüs yazılımının dosya oluşturmayı engellemediğinden emin olun.
*   **`AttributeError: Observer object has no attribute 'timeout'`:**
    *   `watchdog` kütüphanesinin sürümüyle ilgili bir uyumsuzluk olabilir. `pip install --upgrade watchdog` yapın. (v2.2-local bu sorunu `observer = Observer(timeout=...)` ile çözmüştür).
*   **RAM/CPU Verileri Gelmiyor:**
    *   `psutil` kütüphanesinin yüklü olduğundan emin olun (`pip show psutil`).

---

## 🤝 Katkıda Bulunma

1.  Bu repoyu fork edin.
2.  Yeni bir feature branch oluşturun (`git checkout -b feature/yenilik`).
3.  Değişikliklerinizi commit edin (`git commit -m 'Yeni özellik eklendi'`).
4.  Branch'inizi push edin (`git push origin feature/yenilik`).
5.  Bir Pull Request oluşturun.

---

*v2.2-local © 2026 Black Box Deep Analytics*
