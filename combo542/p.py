# === Imports ===
import os
import tkinter as tk
import threading
import requests
import wave
import time
import pyaudio
import openai
import asyncio

from dotenv import load_dotenv
from deepgram import Deepgram

# === Load API Keys ===
load_dotenv()
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY   = os.getenv("DEEPGRAM_API_KEY")
openai.api_key     = OPENAI_API_KEY

# === Initialize Deepgram client ===
deepgram_client = Deepgram(DEEPGRAM_API_KEY)

# === Audio Config ===
SAMPLE_RATE    = 16000
CHANNELS       = 1
FORMAT         = pyaudio.paInt16
CHUNK          = 1024
RECORD_SECONDS = 8
TEMP_WAV       = "temp_audio.wav"

# === Runtime Flag ===
stop_flag  = False
dark_mode  = False

# === TTS: Deepgram Aura ===
def speak(text):
    start = time.time()
    try:
        cleaned_text = text.strip()
        if not cleaned_text:
            print("🔴 TTS Error: Empty text")
            return

        url = "https://api.deepgram.com/v1/speak"
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": cleaned_text,
            "model": "aura-asteria-en",
            "encoding": "linear16",
            "sample_rate": SAMPLE_RATE
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.ok:
            stream = pyaudio.PyAudio().open(format=FORMAT,
                                            channels=CHANNELS,
                                            rate=SAMPLE_RATE,
                                            output=True)
            stream.write(response.content)
            stream.stop_stream()
            stream.close()
            print(f"🔊 TTS time: {round(time.time() - start, 2)}s")
        else:
            print("🔴 Deepgram:", response.text)
    except Exception as e:
        print("🔴 TTS Exception:", e)

# === STT: Deepgram ===
async def transcribe(path):
    try:
        with open(path, "rb") as f:
            source  = {"buffer": f, "mimetype": "audio/wav"}
            options = {"punctuate": True, "model": "nova-2"}
            resp    = await deepgram_client.transcription.prerecorded(source, options)
            return resp["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception as e:
        print("Deepgram STT Error:", e)
        return None

# === GPT-4 Nano ===
def chat_gpt(prompt):
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
        return reply
    except Exception as e:
        print("🔴 GPT Error:", e)
        return "Sorry, GPT error."

# === Main Voice Flow ===
def handle_voice():
    def task():
        global stop_flag
        stop_flag = False
        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)
        status.set("🎙 Recording...")
        mic_icon.config(text="🎤", fg="green")

        # Record audio
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
                        input=True, frames_per_buffer=CHUNK)
        frames = [stream.read(CHUNK, exception_on_overflow=False)
                  for _ in range(int(SAMPLE_RATE / CHUNK * RECORD_SECONDS))]
        stream.stop_stream(); stream.close(); p.terminate()

        # Save WAV
        wf = wave.open(TEMP_WAV, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
        wf.close()

        # Transcribe
        transcript = asyncio.run(transcribe(TEMP_WAV))
        mic_icon.config(text="")
        if stop_flag or not transcript:
            status.set("⏹️ Stopped or failed")
            return

        input_text.insert(tk.END, transcript)
        status.set("🤖 Thinking...")
        reply = chat_gpt(transcript)
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
    for w in main_frame.winfo_children():
        w.config(bg=panel, fg=fg)
    input_text.config(bg=panel, fg=fg, insertbackground=fg)
    chat_output.config(bg=panel, fg=fg, insertbackground=fg)
    mic_button.config(bg="#7289da" if dark_mode else "#007acc", fg="white")
    stop_button.config(bg="#ff5555", fg="white")

# === UI Setup ===
window = tk.Tk()
window.title("🎤 Voice Assistant | Deepgram + GPT-4 Nano")
window.geometry("950x620")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="🎤 Deepgram TTS/STT + GPT-4", font=("Arial", 18, "bold"), fg="white", bg="#007acc").pack(side="left", padx=10)
tk.Button(header, text="Toggle Theme", command=toggle_theme, bg="#7289da", fg="white").pack(side="right", padx=10)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")
tk.Label(main_frame, text="Your Question:", bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4)
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial", 14), fg="green", bg="white")
mic_icon.pack()

btn_frame = tk.Frame(main_frame, bg="white")
btn_frame.pack(pady=10)
mic_button = tk.Button(btn_frame, text="🎤 Speak", command=handle_voice, bg="#007acc", fg="white", padx=20, pady=10)
mic_button.pack(side="left", padx=5)
stop_button = tk.Button(btn_frame, text="🛑 Stop", command=stop_voice, bg="#ff5555", fg="white", padx=20, pady=10)
stop_button.pack(side="left", padx=5)

tk.Label(main_frame, text="Response:", bg="white").pack(anchor="w", pady=(10, 0))
chat_output = tk.Text(main_frame, height=10)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken", anchor="w", bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()