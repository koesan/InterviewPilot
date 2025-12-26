import sys
import time
import threading
import april_asr as april
import sounddevice as sd
import google.generativeai as genai
import deepl
import os
from dotenv import load_dotenv
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QScrollArea, QFrame, QShortcut)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QCursor, QFont, QKeySequence

# Load environment variables (Robust Path)
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_status = load_dotenv(env_path)

if not load_status:
    print(f"DEBUG: .env file NOT loaded. Checked path: {env_path}")
else:
    print(f"DEBUG: .env loaded successfully from {env_path}")

# --- API AYARLARI ---
# Keys are now loaded from .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPL_KEY = os.getenv("DEEPL_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")



SYSTEM_PROMPT = """
ROLE: You are an Expert Software Engineer and Career Coach. You are assisting a candidate in a technical interview.

--- INSTRUCTIONS ---

1. Analyze the input question and the context.
2. Provide a structured, professional, and concise answer suitable for a technical interview.
3. If the input is a question about the candidate's background, use the examples below as a template but adapt them to be generic if no specific details are provided.

--- EXAMPLE PERSONA (Edit this section to match your CV) ---

Background: Computer Engineering Graduate, strong interest in AI and Autonomous Systems.
Skills: Python, C++, ROS, Docker, Deep Learning.
Key Achievements: 1st Place in National Hackathons.

--- CORE SPEAKING RULES ---

- Be Direct and "Results-Oriented".
- Use simple, clear English (B1/B2 level).
- Avoid filler words. Use connectors like "Actually," or "To be specific,".

--- EXPECTED OUTPUT FORMAT ---

Provide the answer directly as if you are the candidate speakng.
"""



def get_best_model():
    models = ["models/gemini-3-flash-preview"]
    for m in models:
        try:
            mod = genai.GenerativeModel(m)
            return mod
        except: continue
    return None

active_model = get_best_model()

# --- STİL DOSYASI ---
DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #121212;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
}
QScrollArea {
    border: none;
    background-color: #121212;
}
QScrollBar:vertical {
    border: none;
    background: #1e1e1e;
    width: 10px;
    margin: 0px; 
}
QScrollBar::handle:vertical {
    background: #444;
    min-height: 20px;
    border-radius: 5px;
}
"""

# --- KART WIDGET ---
class ConversationCard(QFrame):
    clicked_signal = pyqtSignal(object) 

    def __init__(self, english_text, tr_text, ai_answer):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.is_focused = False
        
        self.default_style = """
            QFrame {
                background-color: #1e1e1e;
                border-radius: 12px;
                border: 1px solid #333;
                margin-bottom: 12px;
            }
        """
        self.focused_style = """
            QFrame {
                background-color: #252526;
                border-radius: 12px;
                border: 2px solid #00e676; 
                margin-bottom: 12px;
            }
        """
        self.setStyleSheet(self.default_style)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        lbl_q = QLabel(f"🗣 {english_text}")
        lbl_q.setWordWrap(True)
        lbl_q.setStyleSheet("color: #4fc3f7; font-size: 16px; font-weight: 600; border: none; background: transparent;")
        layout.addWidget(lbl_q)
        
        lbl_tr = QLabel(f"{tr_text}")
        lbl_tr.setWordWrap(True)
        lbl_tr.setStyleSheet("color: #9e9e9e; font-style: italic; font-size: 14px; border: none; background: transparent;")
        layout.addWidget(lbl_tr)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #333; max-height: 1px; margin-top: 5px; margin-bottom: 5px; border: none;")
        layout.addWidget(line)
        
        lbl_ans = QLabel(f"{ai_answer}")
        lbl_ans.setWordWrap(True)
        lbl_ans.setStyleSheet("color: #00e676; font-weight: bold; font-size: 20px; border: none; background: transparent;")
        lbl_ans.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(lbl_ans)
        
        self.setLayout(layout)

    def mousePressEvent(self, event):
        self.clicked_signal.emit(self)
        super().mousePressEvent(event)

    def set_focus(self, focused):
        self.is_focused = focused
        self.setStyleSheet(self.focused_style if focused else self.default_style)

# --- AI THREAD (OPTIMIZED: PARALLEL & LOW LATENCY) ---
import concurrent.futures

class AIThread(QThread):
    result_ready = pyqtSignal(str, str, str)
    
    def __init__(self):
        super().__init__()
        self.queue = []
        self.lock = threading.Lock()
        self.running = True
        self.history = [] 
        self.req_id = 0 # İstek sayacı (Eski istekleri iptal etmek için)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        
        try: self.deepl = deepl.Translator(DEEPL_KEY)
        except: self.deepl = None

    def add_task(self, text):
        with self.lock:
            # Yeni bir konuşma geldiyse, kuyruğu temizle ve sayacı artır
            self.queue.clear() 
            self.req_id += 1
            self.queue.append((text, self.req_id))

    def clear_all(self):
        with self.lock:
            self.queue.clear()
            self.req_id += 1 # Mevcut işlenenleri de 'stale' (eski) durumuna düşür
        self.history.clear()

    def run(self):
        while self.running:
            task = None
            
            with self.lock:
                if self.queue: 
                    task = self.queue.pop(0)
            
            if task:
                text, task_id = task
                
                # 1. Erken Kontrol: Eğer işlem sırasındayken yeni bir istek geldiyse bunu atla
                if task_id != self.req_id:
                    continue

                # Context Yönetimi
                self.history.append(f"Interviewer: {text}")
                if len(self.history) > 5: self.history.pop(0)
                context_str = "\n".join(self.history)

                # 2. PARALEL İŞLEM (DeepL ve Gemini aynı anda başlasın)
                future_tr = self.executor.submit(self._translate, text)
                future_ans = self.executor.submit(self._get_answer, text, context_str)
                
                # Sonuçları bekle (Timeout ekle ki takılmasın)
                try:
                    tr = future_tr.result(timeout=4)
                except: tr = "..."
                
                try:
                    ans = future_ans.result(timeout=7)
                except: ans = "..."

                # 3. Son Kontrol: İşlem bittiğinde hala en güncel istek bu mu?
                # Eğer kullanıcı bu arada başka bir şey dediyse (req_id arttıysa), bunu çöpe at.
                if task_id == self.req_id:
                    self.result_ready.emit(text, tr, ans)
            
            self.msleep(10) # CPU'yu rahatlat ama çok bekleme

    def _translate(self, text):
        if not self.deepl: return "DeepL Yok (Not Found)"
        try: return self.deepl.translate_text(text, target_lang="TR").text
        except: return "Çeviri Hatası (Transl. Error)"

    def _get_answer(self, text, context):
        if not active_model: return "API Hatası (API Error)"
        
        prompt = f"""
        {SYSTEM_PROMPT}
        --- CONVERSATION HISTORY (Last 5 turns) ---
        {context}
        --- INPUT ---
        "{text}"
        """
        try:
            # Hız için content generation config süresi kısılabilir ama default iyidir.
            response = active_model.generate_content(prompt)
            return response.text.strip()
        except Exception: 
            return "..."

# --- ANA ARAYÜZ ---
class InterviewApp(QWidget):
    asr_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("InterviewPilot - Yapay Zeka Mülakat Asistanı (AI Interview Assistant)")
        self.setGeometry(100, 100, 550, 850)
        
        self.is_listening = True 
        self.auto_scroll = True 
        
        # Smart Buffer
        self.speech_buffer = "" 
        self.buffer_timer = QTimer()
        self.buffer_timer.setSingleShot(True)
        self.buffer_timer.timeout.connect(self.process_buffered_speech)
        
        self.setup_ui()
        
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcut_space.activated.connect(self.toggle_listening)
        
        self.shortcut_enter = QShortcut(QKeySequence(Qt.Key_Return), self)
        self.shortcut_enter.activated.connect(self.clear_history)

        self.init_april()
        self.ai_thread = AIThread()
        self.ai_thread.result_ready.connect(self.add_card)
        self.ai_thread.start()
        
        self.asr_signal.connect(self.handle_asr)

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.status_bar = QLabel("DİNLİYOR / LISTENING (SPACE: Durdur/Stop)")
        self.status_bar.setAlignment(Qt.AlignCenter)
        self.status_bar.setFixedHeight(45)
        self.status_bar.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.status_bar.setStyleSheet("background-color: #2e7d32; color: white;")
        main_layout.addWidget(self.status_bar)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        
        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("background-color: #121212;")
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setAlignment(Qt.AlignTop)
        self.container_layout.setContentsMargins(15, 15, 15, 15)
        
        self.scroll.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll)
        
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #1e1e1e; border-top: 1px solid #333;")
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(10, 8, 10, 8)
        
        self.lbl_partial = QLabel("...")
        self.lbl_partial.setStyleSheet("color: #888; font-style: italic; font-size: 15px; border: none;")
        self.lbl_partial.setFixedHeight(25)
        bottom_layout.addWidget(self.lbl_partial)

        info_lbl = QLabel("SPACE: Durdur/Başlat (Stop/Start) | ENTER: Temizle (Clear) | TIKLA: Sabitle (Focus)")
        info_lbl.setStyleSheet("color: #666; font-size: 11px; font-weight: bold; border: none;")
        info_lbl.setAlignment(Qt.AlignCenter)
        bottom_layout.addWidget(info_lbl)
        
        main_layout.addWidget(bottom_frame)
        self.setLayout(main_layout)

    def toggle_listening(self):
        self.is_listening = not self.is_listening
        if self.is_listening:
            self.status_bar.setText("DİNLİYOR / LISTENING (SPACE: Durdur/Stop)")
            self.status_bar.setStyleSheet("background-color: #2e7d32; color: white;")
        else:
            self.status_bar.setText("DURAKLATILDI / PAUSED (Mikrofon Kapalı / Mic Off)")
            self.status_bar.setStyleSheet("background-color: #c62828; color: white;")
            self.lbl_partial.setText("...")
            # Durdurulunca buffer timer'ı da durdur
            self.buffer_timer.stop()
            self.process_buffered_speech() # Kalan varsa gönder

    def clear_history(self):
        # 1. UI Temizliği
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()
        
        # 2. Buffer Temizliği (ÖNEMLİ: Kalan sesleri sil)
        self.speech_buffer = ""
        self.buffer_timer.stop()
        self.lbl_partial.setText("...")
        
        # 3. Backend Temizliği (Reset Flag tetikle)
        self.ai_thread.clear_all()
        self.auto_scroll = True
        
        if self.is_listening:
             self.status_bar.setStyleSheet("background-color: #2e7d32; color: white;")
             self.status_bar.setText("DİNLİYOR / LISTENING (Sıfırlandı/Reset)")

    def add_card(self, eng, tr, ans):
        if not ans or len(ans) < 2: return
        card = ConversationCard(eng, tr, ans)
        card.clicked_signal.connect(self.handle_card_click)
        self.container_layout.addWidget(card)
        if self.auto_scroll:
            QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def handle_card_click(self, clicked_card):
        if clicked_card.is_focused:
            clicked_card.set_focus(False)
            self.auto_scroll = True
            if self.is_listening:
                self.status_bar.setText("DİNLİYOR / LISTENING (Devam/Resuming)")
                self.status_bar.setStyleSheet("background-color: #2e7d32; color: white;")
            self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        else:
            for i in range(self.container_layout.count()):
                widget = self.container_layout.itemAt(i).widget()
                if isinstance(widget, ConversationCard): widget.set_focus(False)
            clicked_card.set_focus(True)
            self.auto_scroll = False
            self.status_bar.setText("ODAKLANDI / FOCUSED (Devam için Tıkla / Click into Resume)")
            self.status_bar.setStyleSheet("background-color: #f57f17; color: white;")

    def init_april(self):
        try: self.model = april.Model("april-english-dev-01110_en.april")
        except: return
        
        def cb(t, tokens):
            txt = "".join(x.token for x in tokens).strip()
            if txt:
                if t == april.Result.FINAL_RECOGNITION:
                     self.asr_signal.emit(f"FINAL:{txt}")
                else:
                     self.asr_signal.emit(f"PARTIAL:{txt}")

        self.session = april.Session(self.model, cb, asynchronous=True)
        
        def audio_cb(d, f, t, s):
            if self.is_listening:
                try: self.session.feed_pcm16((d * 32767).astype("short").astype("<u2").tobytes())
                except: pass
        
        try:
            self.stream = sd.InputStream(samplerate=16000, channels=1, callback=audio_cb)
            self.stream.start()
        except: pass

    def handle_asr(self, signal_text):
        if not self.is_listening: return
        
        type, text = signal_text.split(":", 1)
        
        if type == "PARTIAL":
            self.lbl_partial.setText(self.speech_buffer + " " + text + "...")
            # 2.5 saniye sessizlik kuralı (Daha sabırlı olması için artırıldı)
            self.buffer_timer.start(2000) 
            
        elif type == "FINAL":
            if len(text) < 2: return
            self.speech_buffer += text + " "
            self.lbl_partial.setText(self.speech_buffer + "...")
            # 2.5 saniye daha bekle, belki devamı gelir
            self.buffer_timer.start(1000) 

    def process_buffered_speech(self):
        final_text = self.speech_buffer.strip()
        if final_text:
            self.ai_thread.add_task(final_text)
            self.speech_buffer = ""
            self.lbl_partial.setText("Cevap bekleniyor... (Waiting for answer...)") # Kullanıcıya geri bildirim

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    w = InterviewApp()
    w.show()
    sys.exit(app.exec_())