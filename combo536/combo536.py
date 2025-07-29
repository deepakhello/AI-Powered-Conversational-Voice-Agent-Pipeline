import os
import tkinter as tk
import threading
import time
import cohere
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# === Load API keys ===
load_dotenv()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION     = os.getenv("AZURE_REGION")
COHERE_API_KEY   = os.getenv("COHERE_API_KEY")

# === Init Cohere client ===
co = cohere.Client(COHERE_API_KEY)

# globals
force_stop = False
dark_mode  = False

# === Azure STT ===
def transcribe_with_azure():
    t0 = time.perf_counter()
    cfg = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    cfg.speech_recognition_language = "en-US"
    rec = speechsdk.SpeechRecognizer(speech_config=cfg)

    print("🎙 Listening (Azure STT)…")
    result = rec.recognize_once()
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        txt = result.text
    else:
        print("🔴 Azure STT Error:", result.reason)
        txt = ""
    print(f"[Timing] Azure STT: {time.perf_counter()-t0:.2f}s")
    return txt

# === Cohere LLM ===
def chat_with_cohere(prompt: str) -> str:
    t0 = time.perf_counter()
    try:
        resp  = co.chat(model="command-r", message=prompt)
        reply = resp.text.strip()
    except Exception as e:
        print("🔴 Cohere Error:", e)
        reply = "Sorry, I hit an error."
    print("🤖 Cohere Reply:", reply)
    print(f"[Timing] Cohere LLM: {time.perf_counter()-t0:.2f}s")
    return reply

# === Azure TTS ===
def speak(text: str):
    t0 = time.perf_counter()
    cfg = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    cfg.speech_synthesis_voice_name = "en-US-JennyNeural"
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg)
    synth.speak_text_async(text).get()
    print(f"[Timing] Azure TTS: {time.perf_counter()-t0:.2f}s")

# === Main interaction ===
def handle_voice_interaction():
    def task():
        global force_stop
        force_stop = False

        status.set("🎙 Listening...")
        transcript = transcribe_with_azure()

        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)

        if not transcript:
            chat_output.insert(tk.END, "Sorry, I didn't catch that.")
            speak("Sorry, I didn't catch that.")
            status.set("No speech detected")
            return

        input_text.insert(tk.END, transcript)
        status.set("🤖 Thinking...")
        reply = chat_with_cohere(transcript)
        chat_output.insert(tk.END, reply)

        status.set("🔊 Speaking...")
        speak(reply)
        status.set("✅ Done")

    threading.Thread(target=task, daemon=True).start()

# === Stop & Theme ===
def stop_recording():
    global force_stop
    force_stop = True
    status.set("🛑 Recording stopped")

def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg = "#2c2f33" if dark_mode else "#f2f2f2"
    fg = "white" if dark_mode else "black"
    window.config(bg=bg)
    header.config(bg="#7289da" if dark_mode else "#007acc")
    main_frame.config(bg=bg)
    for w in main_frame.winfo_children():
        w.config(bg=bg, fg=fg)

# === Build GUI ===
window = tk.Tk()
window.title("Azure STT + Cohere + Azure TTS")
window.geometry("900x600")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="🎤 Voice Assistant", fg="white", bg="#007acc",
         font=("Arial",18)).pack(side="left", padx=20)
tk.Button(header, text="Toggle Theme", command=toggle_theme,
          bg="#7289da", fg="white").pack(side="right", padx=20)

main_frame = tk.Frame(window, bg="white", padx=20, pady=20)
main_frame.pack(expand=True, fill="both")

tk.Button(main_frame, text="🎤 Speak & Get Answer",
          command=handle_voice_interaction,
          bg="#007acc", fg="white", padx=20, pady=10).pack(pady=(0,10))
tk.Button(main_frame, text="🛑 Stop Recording",
          command=stop_recording,
          bg="#cc0000", fg="white").pack(pady=(0,20))

tk.Label(main_frame, text="Transcript:", bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=3)
input_text.pack(fill="x", pady=(0,10))

tk.Label(main_frame, text="Response:", bg="white").pack(anchor="w")
chat_output = tk.Text(main_frame, height=8)
chat_output.pack(fill="both", expand=True)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken",
         anchor="w", bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()