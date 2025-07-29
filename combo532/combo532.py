import os
import tkinter as tk
import threading
import time
import wave
import pyaudio
import requests
import google.generativeai as genai
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# === Load API keys & models ===
load_dotenv()
GOOGLE_API_KEY       = os.getenv("GOOGLE_API_KEY")
DEEPGRAM_API_KEY     = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_VOICE_MODEL = os.getenv("DEEPGRAM_VOICE_MODEL")  # e.g. "alloy"
AZURE_SPEECH_KEY     = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION         = os.getenv("AZURE_REGION")

# Configure Gemini (Google Generative AI)
genai.configure(api_key=GOOGLE_API_KEY)

# Globals
force_stop = False
dark_mode  = False

# Audio config
SAMPLE_RATE    = 16000
CHANNELS       = 1
FORMAT         = pyaudio.paInt16
CHUNK          = 1024
RECORD_SECONDS = 10
TEMP_WAV       = "deepgram_temp.wav"
TTS_WAV        = "tts_out.wav"

# === Azure STT ===
def transcribe_with_azure():
    t0 = time.perf_counter()
    cfg = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_REGION
    )
    cfg.speech_recognition_language = "en-US"
    recognizer = speechsdk.SpeechRecognizer(speech_config=cfg)

    print("🎙 Listening (Azure STT)...")
    result = recognizer.recognize_once()
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        transcript = result.text
    else:
        print("🔴 Azure STT Error:", result.reason)
        transcript = ""

    print(f"[Timing] Azure STT: {time.perf_counter() - t0:.2f}s")
    return transcript

# === Gemini LLM ===
def chat_with_gemini(prompt: str) -> str:
    t0 = time.perf_counter()
    try:
        resp = genai.chat.completions.create(
            model="chat-bison-001",
            prompt=[{"author":"user","content":prompt}],
            temperature=0.7,
            top_k=40,
            top_p=0.8,
            candidate_count=1
        )
        reply = resp.candidates[0].content.strip()
    except Exception as e:
        print("🔴 Gemini Error:", e)
        reply = "Sorry, Gemini API error."
    print(f"[Timing] Gemini LLM: {time.perf_counter() - t0:.2f}s")
    return reply

# === Deepgram TTS (HTTP) ===
def speak(text: str):
    t0 = time.perf_counter()
    url = "https://api.deepgram.com/v1/speech/synthesize"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPGRAM_VOICE_MODEL,
        "voice": "default",
        "text": text
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, stream=True)
        resp.raise_for_status()
        # write WAV
        with open(TTS_WAV, "wb") as f:
            for chunk in resp.iter_content(CHUNK):
                f.write(chunk)

        # play WAV
        wf = wave.open(TTS_WAV, "rb")
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pa.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )
        data = wf.readframes(CHUNK)
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)

        stream.stop_stream()
        stream.close()
        pa.terminate()
        wf.close()

    except Exception as e:
        print("🔴 Deepgram TTS Error:", e)

    print(f"[Timing] Deepgram TTS: {time.perf_counter() - t0:.2f}s")

# === Main interaction ===
def handle_voice_interaction():
    def task():
        global force_stop
        force_stop = False
        status.set("🎙 Listening...")
        transcript = transcribe_with_azure()

        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)

        if not transcript:
            chat_output.insert(tk.END, "Sorry, I didn't catch that.")
            speak("Sorry, I didn't catch that.")
            status.set("No speech detected")
            return

        input_text.insert(tk.END, transcript)
        status.set("🤖 Thinking...")
        reply = chat_with_gemini(transcript)
        chat_output.insert(tk.END, reply)

        status.set("🔊 Speaking...")
        speak(reply)
        status.set("✅ Done")

    threading.Thread(target=task, daemon=True).start()

# === Stop & Theme ===
def stop_recording():
    global force_stop
    force_stop = True
    status.set("🛑 Recording stopped")

def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg = "#2c2f33" if dark_mode else "#f2f2f2"
    fg = "white" if dark_mode else "black"
    window.config(bg=bg)
    header.config(bg="#7289da" if dark_mode else "#007acc")
    main_frame.config(bg=bg)
    for w in main_frame.winfo_children():
        w.config(bg=bg, fg=fg)

# === Build GUI ===
window = tk.Tk()
window.title("Azure STT + Gemini + Deepgram TTS")
window.geometry("900x600")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(
    header,
    text="🎤 Voice Assistant",
    fg="white", bg="#007acc",
    font=("Arial",18)
).pack(side="left", padx=20)
tk.Button(
    header, text="Toggle Theme", command=toggle_theme,
    bg="#7289da", fg="white"
).pack(side="right", padx=20)

main_frame = tk.Frame(window, bg="white", padx=20, pady=20)
main_frame.pack(expand=True, fill="both")

mic_btn = tk.Button(
    main_frame,
    text="🎤 Speak & Get Answer",
    command=handle_voice_interaction,
    bg="#007acc", fg="white", padx=20, pady=10
)
mic_btn.pack(pady=(0,10))

stop_btn = tk.Button(
    main_frame,
    text="🛑 Stop Recording",
    command=stop_recording,
    bg="#cc0000", fg="white"
)
stop_btn.pack(pady=(0,20))

tk.Label(main_frame, text="Transcript:", bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=3)
input_text.pack(fill="x", pady=(0,10))

tk.Label(main_frame, text="Response:", bg="white").pack(anchor="w")
chat_output = tk.Text(main_frame, height=8)
chat_output.pack(fill="both", expand=True)

status = tk.StringVar(value="Ready")
tk.Label(
    window, textvariable=status, bd=1, relief="sunken",
    anchor="w", bg="#f2f2f2"
).pack(fill="x", side="bottom")

window.mainloop()