import os
import tkinter as tk
import threading
import wave
import pyaudio
import time
import asyncio

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
from deepgram import Deepgram

import cohere

# --- Load API keys ---
load_dotenv()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION     = os.getenv("AZURE_REGION")
COHERE_API_KEY   = os.getenv("COHERE_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# --- Configure clients ---
co = cohere.Client(COHERE_API_KEY)
deepgram_client = Deepgram(DEEPGRAM_API_KEY)

# --- Audio settings ---
CHUNK, RATE    = 1024, 16000
FORMAT         = pyaudio.paInt16
CHANNELS       = 1
RECORD_SECONDS = 5
TEMP_WAV       = "temp.wav"

stop_threads = False
dark_mode    = False

# --- Azure TTS ---
def speak(text):
    if stop_threads:
        return

    try:
        cfg = speechsdk.SpeechConfig(
            subscription=AZURE_SPEECH_KEY,
            region=AZURE_REGION
        )
        cfg.speech_synthesis_voice_name = "en-US-AriaNeural"
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=cfg)
        synthesizer.speak_text_async(text).get()
    except Exception as e:
        status.set("TTS Error")
        print("TTS Error:", e)

# --- Deepgram STT ---
async def transcribe(path):
    try:
        with open(path, "rb") as f:
            source = {"buffer": f.read(), "mimetype": "audio/wav"}
        options = {"punctuate": True, "model": "nova-2"}
        resp = await deepgram_client.transcription.prerecorded(source, options)
        return resp["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception as e:
        print("Deepgram error:", e)
        return None

# --- Cohere LLM call (command-r) ---
def chat_with_cohere(prompt):
    try:
        response = co.chat(
            model="command-r",
            message=prompt
        )
        return response.text.strip()
    except Exception as e:
        print("Cohere error:", e)
        return "Sorry, I couldn't generate a response."

# --- Main voice flow ---
def handle_voice_interaction():
    global stop_threads
    stop_threads = False

    def task():
        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)
        status.set("🎙 Recording...")
        mic_icon.config(text="🎤", fg="green")
        window.update()

        # Record audio
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
        frames = [
            stream.read(CHUNK, exception_on_overflow=False)
            for _ in range(int(RATE / CHUNK * RECORD_SECONDS))
        ]
        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save WAV
        wf = wave.open(TEMP_WAV, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
        wf.close()

        # Transcribe
        status.set("🧠 Transcribing...")
        mic_icon.config(text="⏳")
        window.update()
        transcript = asyncio.run(transcribe(TEMP_WAV))
        os.remove(TEMP_WAV)

        if not transcript:
            chat_output.insert(tk.END, "Could not understand.")
            speak("Sorry, I couldn't understand.")
            status.set("Transcription failed")
            mic_icon.config(text="")
            return

        # Display transcript
        input_text.insert(tk.END, transcript)
        status.set("🧠 Thinking...")
        mic_icon.config(text="")
        window.update()

        # Call Cohere
        reply = chat_with_cohere(transcript)
        if stop_threads:
            status.set("Stopped")
            return

        chat_output.insert(tk.END, reply)
        speak(reply)
        status.set("✅ Response spoken")

    threading.Thread(target=task, daemon=True).start()

# --- Stop button ---
def stop_interaction():
    global stop_threads
    stop_threads = True
    mic_icon.config(text="")
    status.set("🛑 Stopped")

# --- Theme toggle ---
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg      = "#2c2f33" if dark_mode else "#f2f2f2"
    panel   = "#23272a" if dark_mode else "white"
    text_bg = "#2c2f33" if dark_mode else "white"
    text_fg = "white"    if dark_mode else "black"
    accent  = "#7289da"  if dark_mode else "#007acc"

    window.config(bg=bg)
    header.config(bg=accent)
    main_frame.config(bg=panel)
    theme_button.config(bg=accent, fg="white")
    mic_button.config(bg=accent, fg="white")
    stop_button.config(bg=accent, fg="white")

    for w in main_frame.winfo_children():
        w.config(bg=panel, fg=text_fg)
    input_text.config(bg=text_bg, fg=text_fg, insertbackground=text_fg)
    chat_output.config(bg=text_bg, fg=text_fg, insertbackground=text_fg)

# --- UI setup ---
window = tk.Tk()
window.title("🧠 Voice Assistant | Cohere + Deepgram + Azure")
window.geometry("960x640")
window.config(bg="#f2f2f2")

# Header
header = tk.Frame(window, bg="#007acc", height=60)
header.pack(fill="x")
tk.Label(header,
         text="Voice Assistant | Cohere command-r + Deepgram + Azure TTS",
         font=("Arial", 18, "bold"),
         bg="#007acc",
         fg="white").pack(pady=10)
theme_button = tk.Button(header,
                         text="Toggle Theme",
                         font=("Arial", 10),
                         bg="#7289da",
                         fg="white",
                         command=toggle_theme)
theme_button.pack(anchor="e", padx=10)

# Main frame
main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")

tk.Label(main_frame,
         text="Speak your question:",
         font=("Arial", 12),
         bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4, font=("Arial", 11))
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame,
                    text="",
                    font=("Arial", 14),
                    fg="green",
                    bg="white")
mic_icon.pack()

mic_button = tk.Button(main_frame,
                       text="🎤 Tap to Speak",
                       font=("Arial", 13, "bold"),
                       bg="#007acc",
                       fg="white",
                       command=handle_voice_interaction)
mic_button.pack(pady=10)

stop_button = tk.Button(main_frame,
                        text="🛑 Stop",
                        font=("Arial", 13, "bold"),
                        bg="#007acc",
                        fg="white",
                        command=stop_interaction)
stop_button.pack(pady=5)

tk.Label(main_frame,
         text="Assistant Response:",
         font=("Arial", 12, "bold"),
         bg="white").pack(anchor="w", pady=(10, 0))
chat_output = tk.Text(main_frame, height=10, font=("Arial", 11))
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window,
         textvariable=status,
         font=("Arial", 10),
         anchor="w",
         bd=1,
         relief="sunken",
         bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()