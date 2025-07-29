import os
import tkinter as tk
import threading
import requests
import time
import pyaudio
import speech_recognition as sr
import cohere
from dotenv import load_dotenv

# === Load API Keys ===
load_dotenv()
COHERE_API_KEY     = os.getenv("COHERE_API_KEY")
DEEPGRAM_API_KEY   = os.getenv("DEEPGRAM_API_KEY")

co = cohere.Client(COHERE_API_KEY)

# === Audio Config ===
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16

# === Flags ===
stop_requested = False

# === Deepgram TTS ===
def speak(text):
    start = time.time()
    try:
        if not text.strip():
            print("🔴 TTS Error: Empty text")
            return
        url = "https://api.deepgram.com/v1/speak"
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model": "aura-asteria-en",
            "encoding": "linear16",
            "sample_rate": SAMPLE_RATE
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            audio_data = response.content
            stream = pyaudio.PyAudio().open(format=FORMAT,
                                            channels=CHANNELS,
                                            rate=SAMPLE_RATE,
                                            output=True)
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()
            print(f"🔊 TTS time: {round(time.time() - start, 2)}s")
        else:
            print(f"🔴 Deepgram Error: {response.text}")
    except Exception as e:
        print("🔴 Deepgram TTS Error:", e)

# === SpeechRecognition STT ===
def transcribe_with_sr():
    start = time.time()
    try:
        recognizer = sr.Recognizer()
        with sr.Microphone(sample_rate=SAMPLE_RATE) as source:
            status.set("🎙 Listening...")
            mic_icon.config(text="🎤", fg="green")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            mic_icon.config(text="")

        transcript = recognizer.recognize_google(audio)
        print(f"📝 STT time: {round(time.time() - start, 2)}s")
        print("📝 Transcript:", transcript)
        return transcript
    except sr.UnknownValueError:
        print("🔴 Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"🔴 Recognition error: {e}")
        return None

# === Cohere LLM ===
def chat_with_cohere(prompt):
    start = time.time()
    try:
        response = co.chat(
            model="command-r-plus",
            message=prompt,
            temperature=0.7,
            chat_history=[]
        )
        reply = response.text.strip()
        print(f"🤖 LLM time: {round(time.time() - start, 2)}s")
        print("🤖 Cohere Reply:", reply)
        return reply
    except Exception as e:
        print("🔴 Cohere Error:", e)
        return "Sorry, Cohere API error."

# === Voice Interaction ===
def handle_voice_interaction():
    def task():
        global stop_requested
        stop_requested = False
        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)
        status.set("🎙 Recording...")

        transcript = transcribe_with_sr()
        if stop_requested:
            status.set("⏹️ Stopped")
            return
        if not transcript:
            chat_output.insert(tk.END, "Sorry, I didn't catch that.")
            speak("Sorry, I didn't catch that.")
            status.set("No speech detected")
            return

        input_text.insert(tk.END, transcript)
        status.set("🤖 Thinking...")
        reply = chat_with_cohere(transcript)
        if stop_requested:
            status.set("⏹️ Stopped")
            return

        chat_output.insert(tk.END, reply)
        status.set("🔊 Speaking...")
        speak(reply)
        status.set("✅ Done")

    threading.Thread(target=task, daemon=True).start()

# === Stop Interaction ===
def stop_voice_interaction():
    global stop_requested
    stop_requested = True
    status.set("⏹️ Stopping...")
    mic_icon.config(text="")
    print("🛑 Stop requested by user.")

# === Theme Toggle ===
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg     = "#2c2f33" if dark_mode else "#f2f2f2"
    panel  = "#23272a" if dark_mode else "white"
    fg     = "white"   if dark_mode else "black"
    window.config(bg=bg)
    header.config(bg="#7289da" if dark_mode else "#007acc")
    main_frame.config(bg=panel)
    for w in main_frame.winfo_children():
        w.config(bg=panel, fg=fg)
    input_text.config(bg=panel, fg=fg, insertbackground=fg)
    chat_output.config(bg=panel, fg=fg, insertbackground=fg)
    mic_button.config(bg="#7289da" if dark_mode else "#007acc", fg="white")
    stop_button.config(bg="#ff5555", fg="white")

# === GUI Setup ===
dark_mode = False
window = tk.Tk()
window.title("Voice Assistant | STT + Cohere + Deepgram + Timing")
window.geometry("950x620")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="🎤 Assistant | Google STT + Cohere + Deepgram",
         font=("Arial", 18, "bold"), fg="white", bg="#007acc").pack(side="left", padx=10, pady=10)
tk.Button(header, text="Toggle Theme", command=toggle_theme,
          bg="#7289da", fg="white").pack(side="right", padx=10)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")

tk.Label(main_frame, text="Your Question:", bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4)
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial", 14), fg="green", bg="white")
mic_icon.pack()

btn_frame = tk.Frame(main_frame, bg="white")
btn_frame.pack(pady=10)
mic_button = tk.Button(btn_frame, text="🎤 Speak & Get Answer",
                       command=handle_voice_interaction,
                       bg="#007acc", fg="white", padx=20, pady=10)
mic_button.pack(side="left", padx=5)

stop_button = tk.Button(btn_frame, text="🛑 Stop",
                        command=stop_voice_interaction,
                        bg="#ff5555", fg="white", padx=20, pady=10)
stop_button.pack(side="left", padx=5)

tk.Label(main_frame, text="Response:", bg="white").pack(anchor="w", pady=(10, 0))
chat_output = tk.Text(main_frame, height=10)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken", anchor="w",
         bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()