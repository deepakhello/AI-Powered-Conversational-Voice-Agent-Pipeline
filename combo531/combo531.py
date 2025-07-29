import os
import tkinter as tk
import threading
import time
import wave
import pyaudio
import requests
import openai
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# === Load API keys ===
load_dotenv()
DEEPGRAM_API_KEY   = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
AZURE_SPEECH_KEY   = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION       = os.getenv("AZURE_REGION")

openai.api_key = OPENAI_API_KEY

# === Audio settings ===
SAMPLE_RATE    = 16000
CHANNELS       = 1
FORMAT         = pyaudio.paInt16
CHUNK          = 1024
RECORD_SECONDS = 10
TEMP_WAV       = "deepgram_temp.wav"

force_stop = False
dark_mode  = False

# === Text-to-Speech (Azure) ===
def speak(text):
    t0 = time.perf_counter()
    cfg = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_REGION
    )
    cfg.speech_synthesis_voice_name = "en-US-JennyNeural"
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg)
    synth.speak_text_async(text).get()
    t1 = time.perf_counter()
    print(f"[Timing] Azure TTS: {t1 - t0:.2f}s")

# === Deepgram STT via HTTP prerecorded ===
def transcribe_with_deepgram():
    global force_stop
    t0 = time.perf_counter()

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    frames = []
    print("🎙 Recording... (max 10s or press Stop)")

    for _ in range(int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
        if force_stop:
            break
        frames.append(stream.read(CHUNK, exception_on_overflow=False))

    stream.stop_stream()
    stream.close()
    pa.terminate()

    with wave.open(TEMP_WAV, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))

    transcript = ""
    try:
        url = (
            "https://api.deepgram.com/v1/listen"
            "?model=general"
            "&language=en-US"
            "&punctuate=true"
        )
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/wav"
        }
        with open(TEMP_WAV, "rb") as f:
            resp = requests.post(url, headers=headers, data=f)
        resp.raise_for_status()
        data = resp.json()
        transcript = (
            data["results"]["channels"][0]
                ["alternatives"][0]["transcript"]
        )
    except Exception as e:
        print("🔴 Deepgram Error:", e)

    t1 = time.perf_counter()
    print(f"[Timing] Deepgram STT: {t1 - t0:.2f}s")
    return transcript

# === Chat with OpenAI LLM ===
def chat_with_openai(prompt):
    t0 = time.perf_counter()
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        reply = resp.choices[0].message.content.strip()
    except Exception as e:
        print("🔴 OpenAI Error:", e)
        reply = "Sorry, I encountered an error."
    t1 = time.perf_counter()
    print("🤖 OpenAI Reply:", reply)
    print(f"[Timing] OpenAI LLM: {t1 - t0:.2f}s")
    return reply

# === Main voice interaction ===
def handle_voice_interaction():
    def task():
        global force_stop
        force_stop = False
        t_start = time.perf_counter()

        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)

        status.set("🎙 Recording...")
        mic_icon.config(text="🎤", fg="green")
        transcript = transcribe_with_deepgram()
        mic_icon.config(text="")

        if not transcript:
            chat_output.insert(tk.END, "Sorry, I didn't catch that.")
            speak("Sorry, I didn't catch that.")
            status.set("No speech detected")
            return

        input_text.insert(tk.END, transcript)
        status.set("🤖 Thinking...")
        reply = chat_with_openai(transcript)
        chat_output.insert(tk.END, reply)

        status.set("🔊 Speaking...")
        speak(reply)

        t_end = time.perf_counter()
        print(f"[Timing] Total Interaction: {t_end - t_start:.2f}s")
        status.set("✅ Done")

    threading.Thread(target=task, daemon=True).start()

# === Stop recording callback ===
def stop_recording():
    global force_stop
    force_stop = True
    status.set("🛑 Recording stopped")
    mic_icon.config(text="")

# === Theme toggle ===
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg    = "#2c2f33" if dark_mode else "#f2f2f2"
    pane  = "#23272a" if dark_mode else "white"
    fg    = "white"    if dark_mode else "black"

    window.config(bg=bg)
    header.config(bg="#7289da" if dark_mode else "#007acc")
    main_frame.config(bg=pane)
    for w in main_frame.winfo_children():
        w.config(bg=pane, fg=fg)
    input_text.config(bg=pane, fg=fg, insertbackground=fg)
    chat_output.config(bg=pane, fg=fg, insertbackground=fg)
    mic_btn.config(bg="#7289da" if dark_mode else "#007acc")
    stop_btn.config(bg="#cc0000", fg="white")

# === Build GUI ===
window = tk.Tk()
window.title("Voice Assistant | Deepgram + OpenAI + Azure TTS")
window.geometry("950x640")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header,
         text="🎤 Assistant | Deepgram STT + OpenAI + Azure TTS",
         font=("Arial",18,"bold"),
         fg="white", bg="#007acc").pack(pady=10)
tk.Button(header, text="Toggle Theme", command=toggle_theme,
          bg="#7289da", fg="white").pack(anchor="e", padx=10)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")

tk.Label(main_frame, text="Your Question:", bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4)
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial",14),
                    fg="green", bg="white")
mic_icon.pack()

mic_btn = tk.Button(main_frame, text="🎤 Speak & Get Answer",
                    command=handle_voice_interaction,
                    bg="#007acc", fg="white", padx=20, pady=10)
mic_btn.pack(pady=10)

stop_btn = tk.Button(main_frame, text="🛑 Stop Recording",
                     command=stop_recording,
                     bg="#cc0000", fg="white", font=("Arial",11))
stop_btn.pack(pady=5)

tk.Label(main_frame, text="Response:", bg="white").pack(
    anchor="w", pady=(10,0))
chat_output = tk.Text(main_frame, height=10)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken",
         anchor="w", bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()