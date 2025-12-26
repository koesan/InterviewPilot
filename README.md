
# 🎤 InterviewPilot

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

[English](#english) | [Türkçe](#türkçe)

</div>

---

<a name="english"></a>
## 🇺🇸 English

### Overview
**InterviewPilot** is your real-time AI interview assistant. It listens to your interview, transcribes the speech, translates it instantly, and uniquely generates smart, context-aware answers using **Google Gemini AI**.

### Features
- **Real-Time ASR**: Fast and offline speech recognition powered by April-ASR.
- **Smart Answers**: Generates interview-style answers using Google Gemini.
- **Live Translation**: Translates incoming speech using DeepL.
- **Context Awareness**: Remembers the conversation history for better answers.
- **Parallel Processing**: multi-threaded architecture for low latency.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/InterviewPilot.git
   cd InterviewPilot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download ASR Model:**
   - Download `april-english-dev-01110_en.april` from [April-ASR Models](https://abb128.github.io/april-asr/models.html).
   - Place it in the root directory.

4. **Configuration:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - **Google Gemini Key**: Get it from [Google AI Studio](https://aistudio.google.com/). Add it to `GEMINI_API_KEY`.
   - **DeepL Key**: Get it from [DeepL API](https://www.deepl.com/pro-api). Add it to `DEEPL_API_KEY`.

### Usage
Run the application:
```bash
python app.py
```

#### How to Customize (Persona)
Open `app.py` and edits the `SYSTEM_PROMPT` section.
- You can define your own resume, skills, and background there.
- The AI will answer questions based on the persona you define in that code block.

---

<a name="türkçe"></a>
## 🇹🇷 Türkçe

### Genel Bakış
**InterviewPilot**, yapay zeka destekli anlık mülakat asistanınızdır. Mülakatı dinler, konuşulanları yazıya döker, çevirir ve **Google Gemini** kullanarak size teknik mülakatlarda yardımcı olacak akıllı cevaplar üretir.

### Özellikler
- **Gerçek Zamanlı ASR**: April-ASR ile internet gerektirmeyen hızlı ses tanıma.
- **Akıllı Cevaplar**: Google Gemini ile mülakat bağlamına uygun cevap önerileri.
- **Canlı Çeviri**: DeepL ile anlık Türkçe çeviri.
- **Bağlam Hafızası**: Konuşma geçmişini hatırlar ve ona göre cevap verir.
- **Paralel İşlem**: Düşük gecikme için çok iş parçacıklı (multi-threaded) yapı.

### Kurulum

1. **Depoyu klonlayın:**
   ```bash
   git clone https://github.com/your-username/InterviewPilot.git
   cd InterviewPilot
   ```

2. **Gerekli paketleri yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

3. **ASR Modelini İndirin:**
   - `april-english-dev-01110_en.april` dosyasını [April-ASR Modelleri](https://abb128.github.io/april-asr/models.html) sayfasından indirin.
   - Dosyayı ana dizine atın.

4. **Yapılandırma:**
   - `.env.example` dosyasını `.env` olarak kopyalayın:
     ```bash
     cp .env.example .env
     ```
   - **Google Gemini Anahtarı**: [Google AI Studio](https://aistudio.google.com/)'dan alın ve `.env` dosyasına `GEMINI_API_KEY` olarak ekleyin.
   - **DeepL Anahtarı**: [DeepL API](https://www.deepl.com/pro-api)'den alın ve `.env` dosyasına `DEEPL_API_KEY` olarak ekleyin.

### Kullanım
Uygulamayı çalıştırın:
```bash
python app.py
```

#### Kişiselleştirme (Persona)
`app.py` dosyasını açın ve `SYSTEM_PROMPT` bölümünü düzenleyin.
- Kendi CV'nizi, yeteneklerinizi ve geçmişinizi buraya ekleyebilirsiniz.
- Yapay zeka, doğrudan buraya yazdığınız bilgilere göre sanki sizmişsiniz gibi cevap verecektir.

---

## License
MIT License. See [LICENSE](LICENSE) for details.
