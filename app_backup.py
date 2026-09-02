# from flask import Flask, render_template

# app = Flask(__name__)

# @app.route("/")
# def home():
#     return render_template("index.html")

# if __name__ == "__main__":
#     app.run(debug=True)

from flask import Flask, render_template, request, jsonify
import os
import json
import queue
import pyaudio
import requests
import pyttsx3
from vosk import Model, KaldiRecognizer


app = Flask(__name__)


# =========================
# SETTINGS
# =========================

VOSK_MODEL_PATH = "model"

OLLAMA_API_URL = "http://localhost:11434/api/generate"

MODEL_NAME = "llama3.2:1b"


# =========================
# TEXT TO SPEECH
# =========================

engine = pyttsx3.init()

voices = engine.getProperty("voices")

if voices:
    engine.setProperty("voice", voices[0].id)

engine.setProperty("rate", 175)


def speak(text):

    print("Assistant:", text)

    engine.say(text)

    engine.runAndWait()


# =========================
# VOSK MODEL
# =========================

if not os.path.exists(VOSK_MODEL_PATH):

    raise FileNotFoundError(
        "Vosk model folder 'model' not found."
    )


model = Model(VOSK_MODEL_PATH)


# =========================
# OLLAMA
# =========================

def query_ollama(prompt):

    payload = {

        "model": MODEL_NAME,

        "prompt": (
            prompt +
            "\nAnswer briefly and conversationally."
        ),

        "stream": False
    }

    try:

        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:

            return response.json().get(
                "response",
                ""
            ).strip()

        return "Ollama returned an error."

    except requests.exceptions.RequestException:

        return (
            "I cannot connect to Ollama. "
            "Please make sure Ollama is running."
        )


# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():

    return render_template("index.html")


# =========================
# TEXT CHAT
# =========================

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    user_text = data.get("message", "").strip()

    if not user_text:

        return jsonify({
            "response": "Please type something."
        })


    print("You typed:", user_text)


    ai_response = query_ollama(user_text)


    # Speak AI response
    speak(ai_response)


    return jsonify({

        "response": ai_response

    })


# =========================
# VOICE TO TEXT
# =========================

@app.route("/voice")
def voice():

    audio_queue = queue.Queue()

    recognizer = KaldiRecognizer(
        model,
        16000
    )


    mic = pyaudio.PyAudio()


    stream = mic.open(

        format=pyaudio.paInt16,

        channels=1,

        rate=16000,

        input=True,

        frames_per_buffer=4000

    )


    print("\n🎤 Listening...")


    stream.start_stream()


    final_text = ""


    try:

        while True:

            data = stream.read(
                4000,
                exception_on_overflow=False
            )


            if recognizer.AcceptWaveform(data):

                result = json.loads(
                    recognizer.Result()
                )

                final_text = result.get(
                    "text",
                    ""
                ).strip()


                if final_text:

                    break


    finally:

        stream.stop_stream()

        stream.close()

        mic.terminate()


    print("You said:", final_text)


    if not final_text:

        return jsonify({

            "text":"",
            "response":""

        })


    # Send recognized text to Ollama

    ai_response = query_ollama(
        final_text
    )


    # Speak response

    speak(ai_response)


    return jsonify({

        "text": final_text,

        "response": ai_response

    })


# =========================
# RUN
# =========================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )