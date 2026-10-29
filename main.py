import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, 
    QVBoxLayout, QHBoxLayout, QTextEdit, QFileDialog, QSplitter, 
    QComboBox, QFrame
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Google GenAI Kütüphanesi
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# API Anahtarını buraya ekleyebilirsin
GEMINI_API_KEY = "AQ.Ab8RN6LdxmGvtiNx8Vx1X_NikfO88MuTRZ-JEowsd3DwedugBA"

# Arka Planda Donmadan Çalışan AI Analiz İş Parçacığı
class AIAnalysisWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, image_path, api_key):
        super().__init__()
        self.image_path = image_path
        self.api_key = api_key

    def run(self):
        try:
            client = genai.Client(api_key=self.api_key)
            
            with open(self.image_path, "rb") as f:
                image_bytes = f.read()

            prompt = """Sen kıdemli bir acil tıp uzmanı ve kardiyolog gibisin. Bu yüklenen 12 derivasyonlu ECG şeridini bir insan gibi dikkatle, klinik gözle ve titizlikle incele. 
Raporunu şu başlıklar altında samimi, profesyonel, klinik ve açıklayıcı bir dille yaz:
1. Kalibrasyon & Teknik Kalite Kontrolü
2. Ritim ve Kalp Hızı Değerlendirmesi (R-R aralıkları, P dalgası durumu)
3. Aks, QRS Morfolojisi ve İletim Bozuklukları
4. ST Segment ve İskemi / Enfarakt Bulguları (Kritik Tehlike Çanları)
5. Kıdemli Klinisyenin İnsani Yorumu ve Acil Yaklaşım / Triyaj Önerileri"""

            # Güncel model adı kullanıldı
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type='image/jpeg',
                    ),
                    prompt
                ]
            )
            
            report = f"[GEMINI AI GERÇEK GÖRSEL ANALİZ RAPORU] - {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n" + "-"*65 + "\n\n" + response.text
            self.finished.emit(report)

        except Exception as e:
            fallback = f"""[HATA / YEREL SİMÜLASYON RAPORU] - {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
Gemini API hatası: {str(e)}

Lütfen kod içerisindeki GEMINI_API_KEY değişkenine geçerli bir anahtar girdiğinden emin ol."""
            self.finished.emit(fallback)


class ECGDesktopApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Klinik ECG Asistanı & Gemini AI Gözlemcisi")
        self.resize(1300, 850)
        self.current_image_path = None
        self.worker = None
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QLabel {
                color: #f8fafc;
                font-family: 'Segoe UI', Arial;
            }
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #7dd3fc;
                border: 1px solid #38bdf8;
            }
            QPushButton#primaryBtn {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
            }
            QPushButton#primaryBtn:hover {
                background-color: #0369a1;
            }
            QTextEdit {
                background-color: #090d16;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 6px;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 13px;
                padding: 8px;
            }
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QFrame#card {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 8px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Sol Panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("🩺 Klinik ECG & AI Analiz Paneli")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        left_layout.addWidget(title_label)

        image_card = QFrame()
        image_card.setObjectName("card")
        image_layout = QVBoxLayout(image_card)
        
        self.img_label = QLabel("Henüz ECG görseli yüklenmedi.\nDosya seçmek için aşağıdaki butonu kullanın.")
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("color: #64748b; font-size: 14px;")
        self.img_label.setMinimumHeight(380)
        image_layout.addWidget(self.img_label)

        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("📁 ECG Görseli Seç ve AI ile İncele")
        self.load_btn.setObjectName("primaryBtn")
        self.load_btn.clicked.connect(self.load_image)
        btn_layout.addWidget(self.load_btn)

        self.clear_btn = QPushButton("🗑️ Temizle")
        self.clear_btn.clicked.connect(self.clear_image)
        btn_layout.addWidget(self.clear_btn)

        image_layout.addLayout(btn_layout)
        left_layout.addWidget(image_card)

        # Hızlı Senaryo Seçici
        scenario_layout = QHBoxLayout()
        scenario_label = QLabel("Hızlı Klinik Senaryo:")
        scenario_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        scenario_layout.addWidget(scenario_label)

        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems([
            "Özel Senaryo Seçiniz...",
            "Akut İnterior STEMI (DII, DIII, aVF ST Yüksekliği)",
            "Atriyal Fibrilasyon (Düzensiz Düzensizlik, P dalgası yok)",
            "Sol Dal Bloğu (LBBB - V5, V6 çentikli R, Geniş QRS)",
            "Sinüs Taşikardisi (Hız > 100/dk, Normal Morfoloji)"
        ])
        self.scenario_combo.currentIndexChanged.connect(self.load_scenario)
        scenario_layout.addWidget(self.scenario_combo)
        left_layout.addLayout(scenario_layout)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Sağ Panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_title = QLabel("🤖 Gemini AI Klinik Gözlemci Raporu")
        right_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        right_layout.addWidget(right_title)

        self.report_output = QTextEdit()
        self.report_output.setReadOnly(True)
        self.report_output.setPlaceholderText("Yüklediğin ECG görseli yapay zeka tarafından taranacak ve kıdemli bir klinisyen gözüyle detaylı yorumu burada belirecektir...")
        right_layout.addWidget(self.report_output)

        disclaimer_label = QLabel("⚠️ Bu masaüstü uygulama klinik karar destek amacıyla simülasyon olarak tasarlanmıştır. Kesin tanı için resmi tıbbi tetkikler esastır.")
        disclaimer_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        right_layout.addWidget(disclaimer_label)

        splitter.addWidget(right_panel)
        splitter.setSizes([550, 730])

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "ECG Görseli Seç", "", "Görsel Dosyaları (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_name:
            self.current_image_path = file_name
            pixmap = QPixmap(file_name)
            self.img_label.setPixmap(pixmap.scaled(
                self.img_label.width(), self.img_label.height(), 
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
            self.trigger_ai_analysis(file_name)

    def clear_image(self):
        self.current_image_path = None
        self.img_label.clear()
        self.img_label.setText("Henüz ECG görseli yüklenmedi.\nDosya seçmek için aşağıdaki butonu kullanın.")
        self.report_output.clear()
        self.scenario_combo.setCurrentIndex(0)

    def trigger_ai_analysis(self, image_path):
        self.report_output.setPlainText("🔄 ECG görseli Gemini yapay zekasına gönderildi, detaylı klinik tarama ve yorum yapılıyor... Lütfen bekleyin.")
        
        api_key = GEMINI_API_KEY if GEMINI_API_KEY != "BURAYA_API_ANAHTARINI_YAZ" else os.environ.get("GEMINI_API_KEY")

        if not GENAI_AVAILABLE or not api_key:
            self.report_output.setPlainText("⚠️ Hata: 'google-genai' kütüphanesi eksik veya GEMINI_API_KEY girilmemiş.\nLütfen kod içerisindeki API anahtarını tanımlayın.")
            return

        self.worker = AIAnalysisWorker(image_path, api_key)
        self.worker.finished.connect(self.display_ai_report)
        self.worker.start()

    def display_ai_report(self, report_text):
        self.report_output.setPlainText(report_text)

    def load_scenario(self, index):
        if index == 0:
            return
        
        scenarios = {
            1: ("Akut İnterior STEMI Senaryosu", 
                "🚨 KRİTİK KLİNİK UYARI: AKUT İNTERİOR STEMI BULGULARI!\n\n"
                "• Derivasyonlar (DII, DIII, aVF): Bu alanlarda belirgin ST segment yükselmeleri gözleniyor.\n"
                "• Karşıt Bulgular: I ve aVL derivasyonlarında karşılıklı ST çökmesi dikkat çekiyor.\n"
                "• Klinik Yorum: 'Kalbin alt duvarını besleyen damarda ani tıkanıklık şüphesi var. Zaman kaybetmeden acil triyaj ve kardiyoloji konsültasyonu gerekir.'"),
            
            2: ("Atriyal Fibrilasyon (AF) Senaryosu",
                "⚠️ RİTİM UYARISI: ATRİYAL FİBRİLASYON (AF)\n\n"
                "• Ritim Karakteristiği: Düzensiz düzensizlik (Irregularly irregular). R-R mesafeleri tamamen kaotik.\n"
                "• P Dalgaları: Kaybolmuş; yerini f dalgalarına bırakmış."),
            
            3: ("Sol Dal Bloğu (LBBB) Senaryosu",
                "⚠️ İLETİM BOZUKLUĞU: SOL DAL BLOĞU (LBBB)\n\n"
                "• QRS Süresi: Genişlemiş (> 120 ms).\n"
                "• Morfoloji: V5 ve V6'da çentikli geniş R dalgaları, V1-V2'de derin S dalgaları."),
            
            4: ("Sinüs Taşikardisi Senaryosu",
                "ℹ️ FİZYOLOJİK / REAKTİF DURUM: SİNÜS TAŞİKARDİSİ\n\n"
                "• Kalp Hızı: > 100 atım/dakika. P dalgaları normal yerinde ve her QRS'e eşlik ediyor.")
        }

        title, content = scenarios.get(index, ("", ""))
        full_text = f"[{title.upper()}] - Hızlı Referans Senaryosu\n" + "-"*50 + "\n\n" + content
        self.report_output.setPlainText(full_text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ECGDesktopApp()
    window.show()
    sys.exit(app.exec())
