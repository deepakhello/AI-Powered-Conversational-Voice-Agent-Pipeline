import os
import tkinter as tk
import threading
import time
import pyaudio
import pyttsx3
import wave
import openai
from dotenv import load_dotenv

# === Load Keys ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# === Audio Config ===
SAMPLE_RATE = 16000
CHANNELS    = 1
FORMAT      = pyaudio.paInt16
CHUNK       = 1024
RECORD_SECONDS = 8
TEMP_WAV    = "temp_whisper.wav"
stop_flag   = False

# === pyttsx3 TTS ===
engine = pyttsx3.init()
def speak(text):
    start = time.time()
    engine.say(text)
    engine.runAndWait()
    print(f"🔊 TTS time: {round(time.time() - start, 2)}s")

# === Whisper STT ===
def transcribe_whisper():
    start = time.time()
    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
                            input=True, frames_per_buffer=CHUNK)
        frames = []
        print("🎙 Recording with Whisper...")
        for _ in range(int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
            if stop_flag:
                print("⛔ Whisper STT stopped")
                stream.stop_stream(); stream.close(); audio.terminate()
                return None
            frames.append(stream.read(CHUNK))
        stream.stop_stream(); stream.close(); audio.terminate()

        with wave.open(TEMP_WAV, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))

        audio_file = open(TEMP_WAV, "rb")
        response = openai.Audio.transcribe("whisper-1", audio_file)
        transcript = response["text"].strip()
        print(f"📝 STT time: {round(time.time() - start, 2)}s")
        print("📝 Transcript:", transcript)
        return transcript
    except Exception as e:
        print("🔴 Whisper STT Error:", e)
        return None

# === GPT-4 Turbo ===
def chat_openai(prompt):
    start = time.time()
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        reply = response.choices[0].message.content.strip()
        print(f"🤖 GPT time: {round(time.time() - start, 2)}s")
        print("🤖 GPT Reply:", reply)
        return reply
    except Exception as e:
        print("🔴 GPT Error:", e)
        return "Sorry, GPT API error."

# === Voice Flow ===
def handle_voice():
    def task():
        global stop_flag
        stop_flag = False
        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)
        status.set("🎙 Recording...")
        mic_icon.config(text="🎤", fg="green")

        transcript = transcribe_whisper()
        mic_icon.config(text="")
        if stop_flag or not transcript:
            status.set("⏹️ Stopped or failed")
            return

        input_text.insert(tk.END, transcript)
        status.set("🤖 Thinking...")
        reply = chat_openai(transcript)
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
    bg    = "#2c2f33" if dark_mode else "#f2f2f2"
    panel = "#23272a" if dark_mode else "white"
    fg    = "white"   if dark_mode else "black"
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
window.title("Voice Assistant | Whisper STT + GPT Turbo + pyttsx3")
window.geometry("950x620")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="🎤 Whisper STT + GPT Turbo + pyttsx3",
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