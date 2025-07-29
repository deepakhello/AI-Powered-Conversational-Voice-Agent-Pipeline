import os
import time
import wave
import asyncio
import threading
import tkinter as tk
import pyaudio
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
import google.generativeai as genai
from deepgram import Deepgram

# --- Load API Keys ---
load_dotenv()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION     = os.getenv("AZURE_REGION")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# --- Clients ---
genai.configure(api_key=GEMINI_API_KEY)
deepgram_client = Deepgram(DEEPGRAM_API_KEY)

# --- Audio Settings ---
CHUNK, RATE     = 1024, 16000
FORMAT          = pyaudio.paInt16
CHANNELS        = 1
RECORD_SECONDS  = 5
TEMP_WAV        = "temp.wav"

stop_threads = False
dark_mode    = False

# --- Safe File Removal ---
def safe_remove(path, retries=5, delay=0.3):
    for _ in range(retries):
        try:
            with open(path, "a"): pass
            os.remove(path)
            return
        except (PermissionError, OSError):
            time.sleep(delay)
    print(f"❌ Could not delete {path}")

# --- TTS ---
def speak(text):
    if stop_threads: return
    try:
        tts_start = time.time()
        cfg = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
        cfg.speech_synthesis_voice_name = "en-US-AriaNeural"
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=cfg)
        synthesizer.speak_text_async(text).get()
        timings["🔈 TTS"] = time.time() - tts_start
    except Exception as e:
        status.set("TTS Error")
        print("TTS Error:", e)

# --- Transcription ---
async def transcribe(path):
    try:
        stt_start = time.time()
        with open(path, "rb") as f:
            source  = {"buffer": f, "mimetype": "audio/wav"}
            options = {"punctuate": True, "model": "nova-2"}
            resp    = await deepgram_client.transcription.prerecorded(source, options)
        timings["📝 Transcribe"] = time.time() - stt_start
        return resp["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception as e:
        print("Deepgram error:", e)
        return None

# --- Gemini Response ---
def chat_with_gemini(prompt):
    try:
        gen_start = time.time()
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        timings["🤖 Gemini"] = time.time() - gen_start
        return response.text.strip()
    except Exception as e:
        print("Gemini error:", e)
        return "Sorry, Gemini couldn't respond."

# --- Main Voice Flow ---
def handle_voice_interaction():
    global stop_threads
    stop_threads = False

    def task():
        global timings
        timings = {}
        total_start = time.time()

        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)
        status.set("🎙 Recording...")
        mic_icon.config(text="🎤", fg="green")

        rec_start = time.time()
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        frames = [stream.read(CHUNK, exception_on_overflow=False) for _ in range(int(RATE / CHUNK * RECORD_SECONDS))]
        stream.stop_stream(); stream.close(); p.terminate()
        timings["🎤 Record"] = time.time() - rec_start

        wf = wave.open(TEMP_WAV, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
        wf.close()

        transcript = asyncio.run(transcribe(TEMP_WAV))
        safe_remove(TEMP_WAV)

        if not transcript:
            chat_output.insert(tk.END, "Could not understand.")
            speak("Sorry, I couldn't understand.")
            status.set("Transcription failed")
            mic_icon.config(text="")
            return

        input_text.insert(tk.END, transcript)
        status.set("🧠 Thinking...")
        mic_icon.config(text="")

        reply = chat_with_gemini(transcript)
        if stop_threads:
            status.set("Stopped")
            return

        chat_output.insert(tk.END, reply)
        speak(reply)

        timings["⏱ Total"] = time.time() - total_start
        status.set("✅ Response spoken")

        print("\n--- Timing Profile ---")
        for k, v in timings.items():
            print(f"{k}: {v:.2f}s")

    threading.Thread(target=task, daemon=True).start()

# --- Stop Interaction ---
def stop_interaction():
    global stop_threads
    stop_threads = True
    mic_icon.config(text="")
    status.set("🛑 Stopped")

# --- Theme Toggle ---
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg        = "#2c2f33" if dark_mode else "#f2f2f2"
    panel     = "#23272a" if dark_mode else "white"
    text_bg   = "#2c2f33" if dark_mode else "white"
    text_fg   = "white"    if dark_mode else "black"
    accent    = "#7289da"  if dark_mode else "#007acc"

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

# --- UI Setup ---
window = tk.Tk()
window.title("🧠 Voice Assistant | Gemini + Deepgram + Azure")
window.geometry("960x640")
window.config(bg="#f2f2f2")

header = tk.Frame(window, bg="#007acc", height=60)
header.pack(fill="x")
tk.Label(header, text="Voice Assistant | Gemini 1.5 Flash + Deepgram + Azure TTS",
         font=("Arial", 18, "bold"), bg="#007acc", fg="white").pack(pady=10)
theme_button = tk.Button(header, text="Toggle Theme", font=("Arial", 10),
                         bg="#7289da", fg="white", command=toggle_theme)
theme_button.pack(anchor="e", padx=10)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")

tk.Label(main_frame, text="Speak your question:", font=("Arial", 12), bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4, font=("Arial", 11))
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial", 14), fg="green", bg="white")
mic_icon.pack()

mic_button = tk.Button(main_frame, text="🎤 Tap to Speak", font=("Arial", 13, "bold"),
                       bg="#007acc", fg="white", command=handle_voice_interaction)
mic_button.pack(pady=10)

stop_button = tk.Button(main_frame, text="🛑 Stop", font=("Arial", 13, "bold"),
                        bg="#007acc", fg="white", command=stop_interaction)
stop_button.pack(pady=5)

tk.Label(main_frame, text="Gemini Response:", font=("Arial", 12, "bold"), bg="white").pack(anchor="w", pady=(10,0))
chat_output = tk.Text(main_frame, height=10, font=("Arial", 11))
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, font=("Arial", 10), anchor="w", bd=1,
         
         relief="sunken", bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()