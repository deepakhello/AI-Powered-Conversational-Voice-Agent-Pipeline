import os
import tkinter as tk
import threading
import requests
import pyaudio
import websocket
import json
import time
import cohere
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# === Load API keys ===
load_dotenv()
AZURE_SPEECH_KEY   = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION       = os.getenv("AZURE_REGION")
COHERE_API_KEY     = os.getenv("COHERE_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# === AssemblyAI v3 Streaming Config ===
API_ENDPOINT = "wss://streaming.assemblyai.com/v3/ws?sample_rate=16000&format_turns=true"
FRAMES_PER_BUFFER = 800
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16

# === Global state ===
stop_event = threading.Event()
transcript_holder = {"text": ""}
audio = None
stream = None
ws_app = None
co = cohere.Client(COHERE_API_KEY)

# === Azure TTS ===
def speak(text):
    cfg = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    cfg.speech_synthesis_voice_name = "en-US-JennyNeural"
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg)
    synth.speak_text_async(text).get()
    print(f"🔊 Speaking: {text}")

# === Cohere LLM ===
def chat_with_cohere(prompt):
    try:
        response = co.chat(model="command-r", message=prompt)
        reply = response.text.strip()
        print("🤖 Cohere:", reply)
        return reply
    except Exception as e:
        print("🔴 Cohere Error:", e)
        return "Sorry, Cohere API error."

# === AssemblyAI WebSocket Handlers ===
def on_open(ws):
    def stream_audio():
        global stream
        while not stop_event.is_set():
            try:
                audio_data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                print("Audio stream error:", e)
                break
    threading.Thread(target=stream_audio, daemon=True).start()

def on_message(ws, message):
    try:
        data = json.loads(message)
        if data.get("type") == "Turn":
            transcript = data.get("transcript", "")
            if transcript and not transcript_holder["text"]:
                transcript_holder["text"] = transcript
                stop_event.set()
    except Exception as e:
        print("Message error:", e)

def on_error(ws, error):
    print("WebSocket error:", error)
    stop_event.set()

def on_close(ws, code, msg):
    print(f"WebSocket closed: {code} {msg}")
    if stream:
        stream.stop_stream()
        stream.close()
    if audio:
        audio.terminate()

# === Start AssemblyAI Streaming ===
def start_transcription():
    global audio, stream, ws_app
    transcript_holder["text"] = ""
    stop_event.clear()

    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
                        input=True, frames_per_buffer=FRAMES_PER_BUFFER)

    ws_app = websocket.WebSocketApp(
        API_ENDPOINT,
        header={"Authorization": ASSEMBLYAI_API_KEY},
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws_thread = threading.Thread(target=ws_app.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

    for _ in range(100):  # ~10 seconds
        if stop_event.is_set():
            break
        time.sleep(0.1)

    try:
        ws_app.close()
    except:
        pass

# === GUI Interaction ===
def handle_voice_interaction():
    def task():
        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)

        status.set("🎙 Listening...")
        mic_icon.config(text="🎤", fg="green")
        start_transcription()
        mic_icon.config(text="")

        user_input = transcript_holder["text"]
        if not user_input:
            chat_output.insert(tk.END, "Sorry, I didn't catch that.")
            speak("Sorry, I didn't catch that.")
            status.set("No speech detected")
            return

        input_text.insert(tk.END, user_input)
        status.set("🤖 Thinking...")
        reply = chat_with_cohere(user_input)
        chat_output.insert(tk.END, reply)
        status.set("🔊 Speaking...")
        speak(reply)
        status.set("✅ Done")

    threading.Thread(target=task, daemon=True).start()

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

# === GUI Setup ===
window = tk.Tk()
window.title("Voice Assistant | AssemblyAI + Cohere + Azure TTS")
window.geometry("950x620")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="🎤 Assistant | AssemblyAI STT + Cohere LLM + Azure TTS",
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

tk.Label(main_frame, text="Response:", bg="white").pack(anchor="w", pady=(10,0))
chat_output = tk.Text(main_frame, height=10)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken", anchor="w",
         bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()