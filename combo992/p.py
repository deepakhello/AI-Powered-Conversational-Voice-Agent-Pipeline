import os
import tkinter as tk
import threading
import time
import pyttsx3
import openai
import speech_recognition as sr
from dotenv import load_dotenv

# === Load API Keys ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# === Audio Config ===
SAMPLE_RATE = 16000
RECORD_SECONDS = 8
stop_flag = False

# === pyttsx3 TTS ===
engine = pyttsx3.init()
def speak(text):
    start = time.time()
    engine.say(text)
    engine.runAndWait()
    print(f"🔊 TTS time: {round(time.time() - start, 2)}s")

# === SpeechRecognition STT ===
def transcribe_sr():
    start = time.time()
    recognizer = sr.Recognizer()
    with sr.Microphone(sample_rate=SAMPLE_RATE) as source:
        print("🎙 Speak now...")
        status.set("🎙 Recording...")
        audio_data = recognizer.listen(source, timeout=RECORD_SECONDS, phrase_time_limit=RECORD_SECONDS)
    try:
        transcript = recognizer.recognize_google(audio_data)
        print(f"📝 STT time: {round(time.time() - start, 2)}s")
        print("📝 Transcript:", transcript)
        return transcript
    except sr.UnknownValueError:
        print("🔴 Could not understand audio")
        return None
    except sr.RequestError as e:
        print("🔴 SR Error:", e)
        return None

# === GPT-4o Response ===
def chat_gpt4o(prompt):
    start = time.time()
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
        print(f"🤖 GPT-4o time: {round(time.time() - start, 2)}s")
        print("🤖 Reply:", reply)
        return reply
    except Exception as e:
        print("🔴 GPT-4o Error:", e)
        return "Sorry, GPT-4o API error."

# === Voice Flow ===
def handle_voice():
    def task():
        global stop_flag
        stop_flag = False
        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)
        status.set("🎙 Recording...")
        mic_icon.config(text="🎤", fg="green")

        transcript = transcribe_sr()
        mic_icon.config(text="")
        if stop_flag or not transcript:
            status.set("⏹️ Stopped or failed")
            return

        input_text.insert(tk.END, transcript)
        status.set("🤖 Thinking...")
        reply = chat_gpt4o(transcript)
        if stop_flag:
            status.set("⏹️ Stopped")
            return

        chat_output.insert(tk.END, reply)
        status.set("🔊 Speaking...")
        speak(reply)
        status.set("✅ Done")

    threading.Thread(target=task, daemon=True).start()

def stop_voice():
    global stop_flag
    stop_flag = True
    status.set("⏹️ Stopping...")
    mic_icon.config(text="")
    print("🛑 Stop requested")

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
    for w in main_frame.winfo_children(): w.config(bg=panel, fg=fg)
    input_text.config(bg=panel, fg=fg, insertbackground=fg)
    chat_output.config(bg=panel, fg=fg, insertbackground=fg)
    mic_button.config(bg="#7289da" if dark_mode else "#007acc", fg="white")
    stop_button.config(bg="#ff5555", fg="white")

# === GUI Setup ===
dark_mode = False
window = tk.Tk()
window.title("Voice Assistant | SR STT + GPT-4o + pyttsx3")
window.geometry("950x620")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="🎤 SR STT + GPT-4o + pyttsx3",
         font=("Arial", 18, "bold"), fg="white", bg="#007acc").pack(side="left", padx=10)
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
mic_button = tk.Button(btn_frame, text="🎤 Speak", command=handle_voice,
                       bg="#007acc", fg="white", padx=20, pady=10)
mic_button.pack(side="left", padx=5)
stop_button = tk.Button(btn_frame, text="🛑 Stop", command=stop_voice,
                        bg="#ff5555", fg="white", padx=20, pady=10)
stop_button.pack(side="left", padx=5)

tk.Label(main_frame, text="Response:", bg="white").pack(anchor="w", pady=(10, 0))
chat_output = tk.Text(main_frame, height=10)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken",
         anchor="w", bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()