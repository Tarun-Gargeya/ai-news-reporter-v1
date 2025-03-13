import google.generativeai as genai
import os
import cv2
import numpy as np
from PIL import Image
from tts.text_to_speech import generate_speech
from ocr_module.preprocess import preprocess_image  

AUDIO_OUTPUT = "output_news.mp3"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def extract_text(image_path):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        processed_image = preprocess_image(image_path)

        processed_pil = Image.fromarray(processed_image)

        response = model.generate_content(["Extract the text from this newspaper article:", processed_pil])

        return response.text.strip() if response.text else "Text extraction failed."
    except Exception as e:
        return f"Error: {e}"

def summarize_text(text):
    """Summarizes extracted text using Gemini."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Summarize this news article:\n\n{text}")
        return response.text.strip() if response.text else "Summarization failed."
    except Exception as e:
        return f"Error: {e}"

def format_news(summary):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"""You are an AI wartime journalist. Convert the following summary into a professional news article.
    - Use a **clear, neutral, and factual** journalistic tone.
    - Keep sentences **concise** and paragraphs **short**.
    - Highlight **key events first**, then **context**, then **expert opinions**.
    - Make the **headline engaging yet factual**.:\n\n{summary}""")
        return response.text.strip() if response.text else "Formatting failed."
    except Exception as e:
        return f"Error: {e}"

def main():
    image_path = "data/raw_images/2c3e3b58-2573-422c-a68c-da00f30284ed.jpg"
    
    print("🔍 Processing:", image_path)
    extracted_text = extract_text(image_path)
    print("\n📰 Extracted Text:\n", extracted_text)

    summary = summarize_text(extracted_text)
    print("\n✍ Summarized Text:\n", summary)

    news_report = format_news(summary)
    print("\n📢 Formatted News Report:\n", news_report)

    generate_speech(news_report, AUDIO_OUTPUT)
    print(f"\n🎙 News report saved as: {AUDIO_OUTPUT}")

# Run the main function
if __name__ == "__main__":
    main()
