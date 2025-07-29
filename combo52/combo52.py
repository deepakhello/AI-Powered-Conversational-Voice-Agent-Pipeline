import os
import tkinter as tk
import threading
import requests
import pyaudio
import wave
import time
from dotenv import load_dotenv
import openai
import azure.cognitiveservices.speech as speechsdk

# === Load API keys ===
load_dotenv()
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
AZURE_SPEECH_KEY   = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION       = os.getenv("AZURE_REGION")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")

openai.api_key = OPENAI_API_KEY

# === Audio Config ===
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1024
RECORD_SECONDS = 10
TEMP_WAV = "temp_audio.wav"
force_stop = False

# === Azure TTS ===
def speak(text):
    t0 = time.perf_counter()
    cfg = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    cfg.speech_synthesis_voice_name = "en-US-JennyNeural"
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg)
    synth.speak_text_async(text).get()
    t1 = time.perf_counter()
    print(f"[Timing] Azure TTS: {t1 - t0:.2f}s")

# === Whisper STT ===
def transcribe_with_whisper():
    global force_stop
    t0 = time.perf_counter()
    try:
        force_stop = False
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
                            input=True, frames_per_buffer=CHUNK)
        frames = []
        print("🎙 Recording...")

        for _ in range(int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
            if force_stop:
                break
            data = stream.read(CHUNK)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        audio.terminate()

        with wave.open(TEMP_WAV, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))

        with open(TEMP_WAV, "rb") as f:
            response = openai.Audio.transcribe("whisper-1", f)
            transcript = response["text"]
            print("📝 Whisper Transcript:", transcript)
            t1 = time.perf_counter()
            print(f"[Timing] Whisper STT: {t1 - t0:.2f}s")
            return transcript
    except Exception as e:
        print("🔴 Whisper Error:", e)
        return None

# === Gemini LLM ===
def chat_with_gemini(prompt):
    t0 = time.perf_counter()
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": GEMINI_API_KEY}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        response = requests.post(url, headers=headers, params=params, json=payload)
        if response.status_code == 200:
            reply = response.json()['candidates'][0]['content']['parts'][0]['text']
            print("🤖 Gemini Reply:", reply)
            t1 = time.perf_counter()
            print(f"[Timing] Gemini LLM: {t1 - t0:.2f}s")
            return reply.strip()
        else:
            print("🔴 Gemini API Error:", response.text)
            return "Sorry, Gemini API error."
    except Exception as e:
        print("🔴 Gemini Exception:", e)
        return "Sorry, Gemini API error."

# === GUI Interaction ===
def handle_voice_interaction():
    def task():
        global force_stop
        t_start = time.perf_counter()
        force_stop = False
        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)

        status.set("🎙 Recording...")
        mic_icon.config(text="🎤", fg="green")
        transcript = transcribe_with_whisper()
        mic_icon.config(text="")

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

        t_end = time.perf_counter()
        print(f"[Timing] Total Interaction: {t_end - t_start:.2f}s")
        status.set("✅ Done")

    threading.Thread(target=task, daemon=True).start()

# === Stop Button ===
def stop_recording():
    global force_stop
    force_stop = True
    status.set("🛑 Recording stopped")
    mic_icon.config(text="")

# === Theme Toggle ===
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg = "#2c2f33" if dark_mode else "#f2f2f2"
    panel = "#23272a" if dark_mode else "white"
    fg = "white" if dark_mode else "black"
    window.config(bg=bg)
    header.config(bg="#7289da" if dark_mode else "#007acc")
    main_frame.config(bg=panel)
    for w in main_frame.winfo_children():
        w.config(bg=panel, fg=fg)
    input_text.config(bg=panel, fg=fg, insertbackground=fg)
    chat_output.config(bg=panel, fg=fg, insertbackground=fg)
    mic_button.config(bg="#7289da" if dark_mode else "#007acc", fg="white")
    stop_btn.config(bg="#cc0000", fg="white")

# === GUI Setup ===
window = tk.Tk()
window.title("Voice Assistant | Whisper + Gemini + Azure TTS")
window.geometry("950x640")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="🎤 Assistant | Whisper STT + Gemini + Azure TTS",
         font=("Arial",18,"bold"), fg="white", bg="#007acc").pack(pady=10)
tk.Button(header, text="Toggle Theme", command=toggle_theme,
          bg="#7289da", fg="white").pack(anchor="e", padx=10)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")

tk.Label(main_frame, text="Your Question:", bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4)
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial",14), fg="green", bg="white")
mic_icon.pack()

mic_button = tk.Button(main_frame, text="🎤 Speak & Get Answer",
                       command=handle_voice_interaction,
                       bg="#007acc", fg="white", padx=20, pady=10)
mic_button.pack(pady=10)

stop_btn = tk.Button(main_frame, text="🛑 Stop Recording",
                     command=stop_recording, bg="#cc0000", fg="white", font=("Arial", 11))
stop_btn.pack(pady=5)

tk.Label(main_frame, text="Response:", bg="white").pack(anchor="w", pady=(10,0))
chat_output = tk.Text(main_frame, height=10)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken", anchor="w",
         bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()