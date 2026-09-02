
import os
import sys
import json
import queue
import requests
import pyaudio
import win32com.client
from vosk import Model, KaldiRecognizer

# ==========================
# CONFIG
# ==========================

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:1b"
VOSK_MODEL_PATH = "model"

# ==========================
# SPEAKER
# ==========================

speaker = win32com.client.Dispatch("SAPI.SpVoice")
speaker.Rate = 0

is_speaking = False

# ==========================
# CHECK MODEL
# ==========================

if not os.path.exists(VOSK_MODEL_PATH):
    print("Model folder not found!")
    sys.exit()

print("Loading Vosk model...")

model = Model(VOSK_MODEL_PATH)
recognizer = KaldiRecognizer(model, 16000)

audio_queue = queue.Queue()

# ==========================
# MIC
# ==========================

mic = pyaudio.PyAudio()

print("Default Mic:")
print(mic.get_default_input_device_info())

def audio_callback(in_data, frame_count, time_info, status):
    global is_speaking

    if not is_speaking:
        audio_queue.put(in_data)

    return (None, pyaudio.paContinue)

stream = mic.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
    input=True,
    input_device_index=1,   # Realtek Mic
    frames_per_buffer=4096,
    stream_callback=audio_callback
)

# ==========================
# SPEAK
# ==========================

def speak(text):
    global is_speaking

    is_speaking = True

    print("\nAssistant:", text)

    try:
        if stream.is_active():
            stream.stop_stream()

        speaker.Speak(str(text))

    except Exception as e:
        print("Speech Error:", e)

    finally:

        if not stream.is_active():
            stream.start_stream()

        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
            except:
                break

        is_speaking = False

# ==========================
# OLLAMA
# ==========================

def ask_ai(prompt):

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    try:

        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            return response.json()["response"].strip()

        return "Sorry, I could not answer."

    except Exception as e:
        print(e)
        return "I cannot connect to Ollama."
    
    # ==========================
# START
# ==========================

print("=" * 50)
print("OFFLINE AI ASSISTANT")
print("=" * 50)

speak("Hello Akshara. I am ready.")

stream.start_stream()

# ==========================
# MAIN LOOP
# ==========================

try:

    while True:

        data = audio_queue.get()

        if recognizer.AcceptWaveform(data):

            result = json.loads(recognizer.Result())

            user_text = result.get("text", "").strip()

            if user_text == "":
                continue

            print("\nYou:", user_text)

            # Exit
            if user_text.lower() in [
                "exit",
                "quit",
                "goodbye",
                "stop"
            ]:
                speak("Goodbye Akshara.")
                break

            print("Sending to AI...")

            ai_response = ask_ai(user_text)

            print("AI:", ai_response)

            speak(ai_response)

except KeyboardInterrupt:

    print("Stopped")

finally:

    stream.stop_stream()
    stream.close()
    mic.terminate()

    print("Assistant Closed")
