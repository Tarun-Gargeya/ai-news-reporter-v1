from gtts import gTTS
import os

def generate_speech(text, output_file="news_report.mp3"):

    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(output_file)
    print(f"Speech saved as {output_file}")

    return output_file

if __name__ == "__main__":
    sample_news = """Breaking News: International peace talks have failed, leading to heightened 
    tensions in the region. World leaders are scrambling to find a diplomatic resolution."""
    
    audio_file = generate_speech(sample_news)
    os.system(f"start {audio_file}")  #jus for testing
    
