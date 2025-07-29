import os
import time
import asyncio
import threading
import wave
import tempfile
import tkinter as tk

import pyaudio
import cohere
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
from deepgram import Deepgram

# === Load API keys ===
load_dotenv()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION     = os.getenv("AZURE_REGION")
COHERE_API_KEY   = os.getenv("COHERE_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# === Clients ===
co        = cohere.Client(COHERE_API_KEY)
deepgram  = Deepgram(DEEPGRAM_API_KEY)

# === Audio settings ===
CHUNK = 1024
RATE  = 16000
FMT   = pyaudio.paInt16
CHANNELS = 1
RECORD_SECONDS = 5
TEMP_WAV = "temp.wav"

stop_threads = False
dark_mode    = False

# === Azure TTS ===
def speak(text):
    global stop_threads
    if stop_threads:
        return
    t0 = time.perf_counter()
    cfg = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    cfg.speech_synthesis_voice_name = "en-US-AriaNeural"
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg)
    synth.speak_text_async(text).get()
    t1 = time.perf_counter()
    print(f"[Timing] Azure TTS: {t1-t0:.3f}s")

# === Deepgram Transcribe ===
async def dg_transcribe(path):
    with open(path, "rb") as f:
        source = {"buffer": f.read(), "mimetype": "audio/wav"}
    options = {"model":"general", "punctuate":True, "smart_format":True}
    return await deepgram.transcription.prerecorded(source, options)

# === Cohere LLM ===
def chat_with_cohere(prompt):
    t0 = time.perf_counter()
    response = co.chat(model="command-r", message=prompt)
    t1 = time.perf_counter()
    print(f"[Timing] Cohere LLM: {t1-t0:.3f}s")
    return response.text.strip()

# === Main Interaction ===
def handle_voice_interaction():
    global stop_threads
    stop_threads = False

    def task():
        t_start = time.perf_counter()

        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)

        # 1) RECORD
        status.set("🎙 Recording...")
        mic_icon.config(text="🎤", fg="green")
        window.update()
        t0 = time.perf_counter()

        p = pyaudio.PyAudio()
        stream = p.open(format=FMT, channels=CHANNELS, rate=RATE,
                        input=True, frames_per_buffer=CHUNK)
        frames = [stream.read(CHUNK, exception_on_overflow=False)
                  for _ in range(int(RATE/CHUNK * RECORD_SECONDS))]
        stream.stop_stream(); stream.close(); p.terminate()

        t1 = time.perf_counter()
        print(f"[Timing] Recording: {t1-t0:.3f}s")

        with wave.open(TEMP_WAV, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FMT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(frames))

        # 2) TRANSCRIBE
        status.set("🧠 Transcribing...")
        mic_icon.config(text="⏳")
        window.update()
        t2 = time.perf_counter()
        result = asyncio.run(dg_transcribe(TEMP_WAV))
        t3 = time.perf_counter()
        print(f"[Timing] Transcription: {t3-t2:.3f}s")
        os.remove(TEMP_WAV)

        try:
            transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
        except Exception as e:
            transcript = ""
            print("[Error] Deepgram response parsing failed:", e)

        if not transcript or not transcript.strip():
            chat_output.insert(tk.END, "Could not understand.")
            speak("Sorry, I couldn't understand.")
            status.set("Transcription failed")
            mic_icon.config(text="")
            print("[Error] Empty transcript passed to Cohere.")
            return

        input_text.insert(tk.END, transcript)
        print(f"[Transcript] {transcript}")

        # 3) LLM CALL
        status.set("🤖 Thinking...")
        mic_icon.config(text="")
        window.update()
        reply = chat_with_cohere(transcript)
        chat_output.insert(tk.END, reply)

        # 4) SPEAK
        status.set("🔊 Speaking...")
        window.update()
        speak(reply)

        t_end = time.perf_counter()
        print(f"[Total] {t_end-t_start:.3f}s\n{'-'*40}")
        status.set("✅ Done")

    threading.Thread(target=task, daemon=True).start()

# === Stop ===
def stop_interaction():
    global stop_threads
    stop_threads = True
    mic_icon.config(text="")
    status.set("🛑 Stopped")

# === Theme Toggle ===
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg       = "#2c2f33" if dark_mode else "#f2f2f2"
    panel    = "#23272a" if dark_mode else "white"
    fg_color = "white"    if dark_mode else "black"
    accent   = "#7289da"  if dark_mode else "#007acc"

    window.config(bg=bg)
    header.config(bg=accent)
    main_frame.config(bg=panel)
    for w in main_frame.winfo_children():
        w.config(bg=panel, fg=fg_color)
    input_text.config(bg=panel, fg=fg_color, insertbackground=fg_color)
    chat_output.config(bg=panel, fg=fg_color, insertbackground=fg_color)
    mic_button.config(bg=accent, fg="white")
    stop_button.config(bg=accent, fg="white")
    theme_button.config(bg=accent, fg="white")

# === GUI Setup ===
window = tk.Tk()
window.title("Voice Assistant | Deepgram + Cohere + Azure TTS")
window.geometry("960x640")
window.config(bg="#f2f2f2")

header = tk.Frame(window, bg="#007acc", height=60)
header.pack(fill="x")
tk.Label(header, text="🎤 Assistant | Deepgram + Cohere + Azure TTS",
         font=("Arial",18,"bold"), bg="#007acc", fg="white").pack(pady=10)
theme_button = tk.Button(header, text="Toggle Theme", command=toggle_theme,
                         bg="#7289da", fg="white", font=("Arial",10))
theme_button.pack(anchor="e", padx=10)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")

tk.Label(main_frame, text="Your Question:", font=("Arial",12), bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4, font=("Arial",11))
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial",14), fg="green", bg="white")
mic_icon.pack()

mic_button = tk.Button(main_frame, text="🎤 Speak & Get Answer",
                       command=handle_voice_interaction,
                       bg="#007acc", fg="white", font=("Arial",13,"bold"),
                       padx=20, pady=10)
mic_button.pack(pady=10)

stop_button = tk.Button(main_frame, text="🛑 Stop",
                        command=stop_interaction,
                        bg="#007acc", fg="white", font=("Arial",13,"bold"),
                        padx=20, pady=5)
stop_button.pack(pady=5)

tk.Label(main_frame, text="Response:", font=("Arial",12,"bold"), bg="white"
        ).pack(anchor="w", pady=(10,0))
chat_output = tk.Text(main_frame, height=10, font=("Arial",11))
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, anchor="w", bd=1, relief="sunken",
         font=("Arial",10), bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()