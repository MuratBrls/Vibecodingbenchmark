# ⚡ VibeBench — Multi-AI Coding Benchmark

**Black Box Deep Analytics Tool** for measuring AI coding performance in real-time.

VibeBench, farklı yapay zeka kodlama asistanlarının (Antigravity, Cursor, Windsurf vb.) performansını gerçek zamanlı senaryolarda, objektif metriklerle karşılaştıran bir benchmark aracıdır.

---

## 🎯 Amaç

Yapay zeka modellerinin kod yazma yeteneklerini sadece "doğruluk" üzerinden değil, aşağıdaki kritik faktörler üzerinden analiz etmek:

*   **⏱️ Hız:** Düşünme (Thinking) ve Kodlama (Writing) süreleri.
*   **🏛️ Mimari Kalite:** OOP kullanımı, fonksiyonel yapı, temiz kod prensipleri.
*   **🛡️ Güvenlik ve Standartlar:** McCabe karmaşıklığı, PEP8 uyumu, güvenlik açıkları.
*   **🖥️ Kaynak Verimliliği:** CPU ve RAM tüketimi (On-Premise modunda).

---

## 🚀 Özellikler (v2.2-local)

*   **🏠 Tam Lokal Çalışma (On-Premise):** Tüm süreç yerel disk üzerinde, ağ gecikmesi olmadan çalışır.
*   **⏱️ Hassas Zamanlama:** `perf_counter` ile milisaniye hassasiyetinde ölçüm.
*   **👀 Watchdog Entegrasyonu:** Dosya sistemi değişikliklerini anlık yakalar.
*   **🖥️ Kaynak Takibi:** `psutil` ile CPU ve RAM kullanımını anlık raporlar.
*   ** Canlı Dashboard:** Terminal üzerinden tüm sürecin canlı takibi.
*   **�️ LocalErrorLogger:** Windows I/O hatalarını (izin, kilit, path uzunluğu) yönetir.

---

## 📦 Kurulum

```powershell
# Projeyi klonlayın
git clone https://github.com/MuratBrls/Vibecodingbenchmark.git
cd Vibecodingbenchmark

# Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt
```

*(Gereksinimler: Python 3.8+, `psutil>=5.9.0`, `watchdog`, `rich`, `pycodestyle`, `mccabe`)*

---

## 🎮 Kullanım

### Benchmark Başlatma

```powershell
python main.py run "Prompt metni buraya" --timeout 600
```

*   **Prompt:** AI modellerine dağıtılacak görev metni.
*   **--no-clean:** Eski çıktıları silmeden çalıştırır.
*   **--timeout N:** Zaman aşımı süresi (varsayılan: 600sn).

### Durum Kontrolü

```powershell
python main.py status
```

---

## 📋 AI Protokolü

Benchmark'a katılan her AI şu protokolü uygulamalıdır:

1.  **Start Sinyali:** Çalışma klasörüne `start_signal.json` oluştur. *(Bu, "Düşünme"yi bitirir, "Yazma"yı başlatır)*
2.  **Kodlama:** İstenen kodu yaz ve kaydet. *(Bu, "Yazma" süresini belirler)*
3.  **End Sinyali:** İşlem bitince `start_signal.json` dosyasını sil. *(Bu, görevi tamamlar)*

---

## 📊 Puanlama Sistemi (Total Score)

| Metrik | Ağırlık | Açıklama |
| :--- | :---: | :--- |
| **⏱️ Hız** | **30%** | Toplam süre (Düşünme + Yazma). |
| **🏛️ Mimari** | **30%** | Yapısal analiz, McCabe skoru, Temiz Kod. |
| **❌ Hata** | **25%** | Her hata veya retry girişimi puan siler. |
| **💎 Kütüphane** | **15%** | Gereksiz import kullanımı cezalandırılır. |

---

## 📁 Dizin Yapısı

*   `main.py`: Ana CLI uygulaması.
*   `watcher.py`: Dosya izleme ve zamanlama motoru.
*   `telemetry.py`: Kaynak ve işlem takibi.
*   `scorer.py`: Puanlama motoru.
*   `dashboard.py`: Terminal arayüzü.
*   `local_error_logger.py`: Hata yönetimi.
*   `logs/`: JSON ve HTML raporları.
*   `test-bench*`: AI çalışma alanları.

---

*© 2026 Black Box Deep Analytics*
