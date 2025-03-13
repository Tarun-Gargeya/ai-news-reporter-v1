import sys
import os
import google.generativeai as genai
from PIL import Image
import time
import cv2
from textblob import TextBlob
import random
import numpy as np
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QPushButton, QFileDialog, QTextEdit, QListWidget, QProgressBar, QSlider, QHBoxLayout ,QLabel
)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal, QUrl
from tts.text_to_speech import generate_speech
from ocr_module.preprocess import preprocess_image 
from news.live_news_api import fetch_live_news
import newspaper  # Requires the `newspaper3k` library
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
AUDIO_OUTPUT = os.path.join("data", "audio", "output_news.mp3")
wav_path = "data/audio/output_news.wav"

class AudioThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, text, output_file):
        super().__init__()
        self.text = text
        self.output_file = output_file

    def run(self):
        for i in range(1, 101, 10):  # Simulate progress
            self.progress.emit(i)
            time.sleep(0.3)

        generate_speech(self.text, self.output_file)
        self.progress.emit(100)
        self.finished.emit()
        
class NewsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Wartime Reporter")
        self.setGeometry(100, 100, 900, 600)
        self.setStyleSheet("""
    /* Make the entire window background dark */
    QWidget {
        background-color: #2B2B2B;
        color: white;
    }

    /* Set the header (tab bar) background to dark gray */
    QTabWidget::pane {
        border: none;
        background: #2B2B2B;
    }
    QTabBar::tab {
        background: #3C3F41;
        color: white;
        padding: 8px;
        border: 1px solid #2B2B2B;
    }
    QTabBar::tab:selected {
        background: #55585A;
        font-weight: bold;
    }

    /* Set all text areas to gray with white text */
    QTextEdit, QLineEdit {
        background: #3C3F41;
        color: white;
        border: 1px solid #55585A;
        padding: 5px;
    }

    /* Set all buttons to gray by default */
    QPushButton {
        background-color: #3C3F41;
        color: white;
        border: 1px solid #55585A;
        padding: 8px;
        font-size: 14px;
    }
    
    /* Make the Process and Extract Audio buttons stand out */
    QPushButton#processButton {
        background-color: rgba(60, 63, 65, 200); /* Slightly transparent buttons */
        color: white;
        border: 1px solid rgba(85, 88, 90, 220);
        padding: 8px;
        font-size: 14px;
    }
    QPushButton#extractAudioButton {
        background-color: #008000; /* Green */
        color: white;
    }

    /* Make labels white for better visibility */
    QLabel {
        color: white;
    }
""")




        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tabs
        self.tab_main = QWidget()
        self.tab_options = QWidget()
        self.tab_live_news = QWidget()
        self.tab_settings = QWidget()

        self.tabs.addTab(self.tab_main, "Gist of What's Happening")
        self.tabs.addTab(self.tab_options, "More Specific Options")
        self.tabs.addTab(self.tab_live_news, "Live News")
        self.tabs.addTab(self.tab_settings, "Settings")

        self.init_main_tab()
        self.init_options_tab()
        self.init_live_news_tab()
        self.init_settings_tab()

    def init_main_tab(self):
        layout = QVBoxLayout()

        self.upload_button = QPushButton("Upload Image")
        self.upload_button.clicked.connect(self.upload_image)

        self.extracted_text = QTextEdit()
        self.extracted_text.setReadOnly(True)
        self.extracted_text.setPlaceholderText("Extracted text will appear here...")

        self.process_button = QPushButton("Process")
        self.process_button.clicked.connect(self.process_image)

        self.audio_button = QPushButton("Generate Audio Report")
        self.audio_button.clicked.connect(self.play_news_audio)

        self.avatar_label = QLabel()
        self.avatar_closed = QPixmap("assets/reporter/close.png")
        self.avatar_open = QPixmap("assets/reporter/open.png")
        self.avatar_label.setPixmap(self.avatar_closed)  # Default closed mouth
        self.avatar_label.setFixedSize(400, 400)  # Set a fixed size
        self.avatar_label.setScaledContents(True)  # Scale the image properly

        self.audio_progress_bar = QProgressBar()
        self.audio_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.audio_progress_bar.setValue(0)
        self.audio_progress_bar.hide()

        # 🎵 **Media Player & Audio Output**
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        # 🔊 **Slider for Audio Seek**
        self.audio_slider = QSlider(Qt.Orientation.Horizontal)

        self.audio_slider.setRange(0, 100)
        self.audio_slider.setEnabled(False)
        self.audio_slider.sliderMoved.connect(self.set_audio_position)

        # ▶ **Playback Controls**
        self.play_button = QPushButton("▶")
        self.pause_button = QPushButton("⏸")
        self.resume_button = QPushButton("⏯")
        self.stop_button = QPushButton("⏹")

        self.play_button.clicked.connect(self.play_audio)
        self.pause_button.clicked.connect(self.pause_audio)
        self.resume_button.clicked.connect(self.resume_audio)
        self.stop_button.clicked.connect(self.stop_audio)
        text_avatar_layout = QHBoxLayout()
        text_avatar_layout.addWidget(self.avatar_label)
        text_avatar_layout.addWidget(self.extracted_text)
        
        layout.addWidget(self.upload_button)
        layout.addLayout(text_avatar_layout)
        layout.addWidget(self.process_button)
        layout.addWidget(self.audio_button)
        layout.addWidget(self.audio_progress_bar)
        layout.addWidget(self.audio_slider)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout) 
        
        self.tab_main.setLayout(layout)

        # 🎵 **Connect Signals for Audio Progress**
        self.media_player.positionChanged.connect(self.update_slider)
        self.media_player.positionChanged.connect(self.update_avatar_animation)
        self.media_player.durationChanged.connect(self.update_slider_range)
   
    def init_options_tab(self):
        layout = QVBoxLayout()

        self.extract_text_button = QPushButton("Extract Only Text")
        self.extract_text_button.clicked.connect(self.extract_text_only)

        self.summarize_button = QPushButton("Summarize Only")
        self.summarize_button.clicked.connect(self.summarize_text_only)

        #self.ner_button = QPushButton("Analyze Entities (NER)")
        #self.ner_button.clicked.connect(self.run_ner_analysis)

        self.sentiment_button = QPushButton("Run Sentiment Analysis")
        self.sentiment_button.clicked.connect(self.run_sentiment_analysis)

        layout.addWidget(self.extract_text_button)
        layout.addWidget(self.summarize_button)
        #layout.addWidget(self.ner_button)
        layout.addWidget(self.sentiment_button)

        self.tab_options.setLayout(layout)
    def extract_text_only(self):
        if hasattr(self, 'image_path'):
            self.extracted_text.setText("Extracting text...")

            QTimer.singleShot(1000, lambda: self.extracted_text.setText(self.extract_text(self.image_path)))
        else:
            self.extracted_text.setText("⚠️ No image uploaded. Please upload an image first.")

    def summarize_text_only(self):
        if self.extracted_text.toPlainText():
            self.extracted_text.setText("Summarizing...")

            QTimer.singleShot(1000, lambda: self.extracted_text.setText(self.summarize_text(self.extracted_text.toPlainText())))
        else:
            self.extracted_text.setText("⚠️ No text available to summarize.")
    
    def run_sentiment_analysis(self):
        text = self.extracted_text.toPlainText()
        if not text:
            self.extracted_text.setText("⚠️ No text available for sentiment analysis.")
            return

        self.extracted_text.setText("Analyzing sentiment...")

        def analyze_sentiment(text):
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 (negative) to +1 (positive)

            if polarity > 0:
                return "😀 **Positive News** (Score: {:.2f})".format(polarity)
            elif polarity < 0:
                return "😠 **Negative News** (Score: {:.2f})".format(polarity)
            else:
                return "😐 **Neutral News** (Score: 0.00)"

        QTimer.singleShot(1000, lambda: self.extracted_text.setText(analyze_sentiment(text)))
    def init_live_news_tab(self):
        layout = QVBoxLayout()

        # 🔍 **Keyword Input**
        self.keyword_input = QTextEdit()
        self.keyword_input.setPlaceholderText("Enter keyword (default: war)")
        self.keyword_input.setFixedHeight(30)  # Keep it small

        # 🔄 **Fetch News Button**
        self.fetch_news_button = QPushButton("Fetch Live News")
        self.fetch_news_button.clicked.connect(self.update_live_news)

        # 📋 **List of News Headlines**
        self.news_list = QListWidget()
        self.news_list.itemClicked.connect(self.load_news_article)  # Click to summarize

        layout.addWidget(self.keyword_input)
        layout.addWidget(self.fetch_news_button)
        layout.addWidget(self.news_list)
        self.tab_live_news.setLayout(layout)

        self.news_data = []  # Store (headline, URL) pairs



    def update_live_news(self):
        self.news_list.clear()
        self.news_list.addItem("🔄 Fetching news...")

        # 📌 Get keyword from input or default to "war"
        keyword = self.keyword_input.toPlainText().strip()
        if not keyword:
            keyword = "war"  # Default keyword

        self.news_data = fetch_live_news(keyword)  # Fetch news with keyword

        self.news_list.clear()
        for headline, _ in self.news_data:
            self.news_list.addItem(headline)  # Display headlines



    def load_news_article(self, item):
        
        index = self.news_list.row(item)
        if index >= len(self.news_data):  # Avoid crash
            return
        _, article_url = self.news_data[index]

        if not article_url:
            self.extracted_text.setText("⚠️ Unable to load article.")
            return

        self.extracted_text.setText("📄 Fetching article... Please wait.")
        self.tabs.setCurrentIndex(0)  # Switch to the main tab

        QTimer.singleShot(1000, lambda: self.extract_text_from_url(article_url))  # Fetch article


    def extract_text_from_url(self, url):
        
        try:
            from newspaper import Article  # Lazy import to avoid unnecessary dependencies

            article = Article(url)
            article.download()
            article.parse()

            extracted_text = article.text[:3000]  # Limit text to avoid API overload
            self.extracted_text.setText("📝 Summarizing with AI...")

            QTimer.singleShot(1000, lambda: self.summarize_with_gemini(extracted_text))  # Summarize with Gemini

        except Exception as e:
            self.extracted_text.setText(f"⚠️ Error extracting article: {e}")
    def summarize_with_gemini(self, text):
        """
        Summarizes the extracted article using Gemini AI.
        """
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"""
            You are an AI news assistant. Summarize this article in while keeping the key events.
            - Keep it **concise & factual**.
            - Retain **important details**.
            - **Avoid opinions or unnecessary fluff**.

            **Article:** {text}
            """

            response = model.generate_content(prompt)
            summary = response.text.strip() if response.text else "⚠️ Summarization failed."

            self.extracted_text.setText(summary)

        except Exception as e:
            self.extracted_text.setText(f"⚠️ Gemini AI Error: {e}")

    def init_settings_tab(self):
        layout = QVBoxLayout()
        self.tts_settings_button = QPushButton("Change TTS Voice")
        self.fact_check_button = QPushButton("Enable Fact-Checking (Coming Soon)")
        layout.addWidget(self.tts_settings_button)
        layout.addWidget(self.fact_check_button)
        self.tab_settings.setLayout(layout)

    def upload_image(self):
        file_dialog = QFileDialog()
        filenames, _ = file_dialog.getOpenFileNames(self, "Select Image(s)", "", "Images (*.png *.jpg *.jpeg)")
        if filenames:
            self.image_path = filenames[0]  # Store the first image path
            self.extracted_text.setText("Image uploaded successfully! Click Process.")

    def process_image(self):
        if hasattr(self, 'image_path'):
            self.process_button.setEnabled(False)
            self.extracted_text.setText("Extracting text...")
            QTimer.singleShot(1000, self.extract_step)
        else:
            self.extracted_text.setText("No image uploaded. Please upload an image first.")
    
    import random

    def update_avatar_animation(self, position):
        """Randomly swaps avatar image between open and closed mouth for a more natural effect."""
        # Introduce randomness in speed (faster/slower mouth movements)
        change_speed = random.randint(200, 600)  # Change every 200ms to 600ms

        # Randomize the opening-closing pattern
        if position % change_speed < (change_speed // 2):  
            self.avatar_label.setPixmap(self.avatar_open)
        else:
            self.avatar_label.setPixmap(self.avatar_closed)

    def play_news_audio(self):
        if self.extracted_text.toPlainText():
            self.audio_progress_bar.show()
            self.audio_progress_bar.setValue(0)

            self.audio_thread = AudioThread(self.extracted_text.toPlainText(), AUDIO_OUTPUT)
            self.audio_thread.progress.connect(self.audio_progress_bar.setValue)
            self.audio_thread.finished.connect(self.audio_generation_complete)
            self.audio_thread.start()
        else:
            self.extracted_text.setText("⚠️ No text available for audio conversion.")

    def audio_generation_complete(self):
        self.audio_progress_bar.setValue(100)
        QTimer.singleShot(500, self.audio_progress_bar.hide)

        # 🎵 **Load and Play Audio in App**
        audio_url = QUrl.fromLocalFile(AUDIO_OUTPUT)
        self.media_player.setSource(QUrl.fromLocalFile(AUDIO_OUTPUT))

        self.media_player.play()

        # 🔊 **Enable Slider**
        self.audio_slider.setEnabled(True)

    # 🛠 **Audio Playback Functions**
    def set_audio_position(self, position):
        self.media_player.setPosition(position)

    def update_slider(self, position):
        self.audio_slider.setValue(position)

    def update_slider_range(self, duration):
        self.audio_slider.setRange(0, duration)

    def play_audio(self):
        self.media_player.play()

    def pause_audio(self):
        self.media_player.pause()

    def resume_audio(self):
        self.media_player.play()

    def stop_audio(self):
        self.media_player.stop()
    def extract_text(self, image_path):
        """Extracts text from an image using Gemini API."""
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            processed_image = preprocess_image(image_path)
            processed_pil = Image.fromarray(processed_image)
            response = model.generate_content(["Extract the text from this newspaper article:", processed_pil])
            return response.text.strip() if response.text else "Text extraction failed."
        except Exception as e:
            return f"Error: {e}"
    def extract_step(self):
        extracted_text = self.extract_text(self.image_path)
        self.extracted_text.setText("Summarizing...")
        QTimer.singleShot(1000, lambda: self.summarize_step(extracted_text))
    
    def summarize_step(self, extracted_text):
        summary = self.summarize_text(extracted_text)
        self.extracted_text.setText("Formatting news...")
        QTimer.singleShot(1000, lambda: self.format_step(summary))
    
    def format_step(self, summary):
        formatted_news = self.format_news(summary)
        self.extracted_text.setText(formatted_news)
        self.process_button.setEnabled(True)
    def summarize_text(self, text):
        """Summarizes the extracted text."""
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(f"Summarize this news article:\n\n{text}")
            return response.text.strip() if response.text else "Summarization failed."
        except Exception as e:
            return f"Error: {e}"

    def format_news(self, summary):
        """Formats the summarized text into a news report."""
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(f"""You are an AI wartime journalist. Convert the following summary into a professional news article.
            - Use a **clear, neutral, and factual** journalistic tone.
            - Keep sentences **concise** and paragraphs **short**.
            - Highlight **key events first**, then **context**, then **expert opinions**.
            - Make the **headline engaging yet factual**.\n\n{summary}""")
            return response.text.strip() if response.text else "Formatting failed."
        except Exception as e:
            return f"Error: {e}"
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NewsApp()
    window.show()
    sys.exit(app.exec())  # ✅ PyQt6 Compatible

