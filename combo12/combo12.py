import os
import tkinter as tk
import threading
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
import requests
import pyaudio
import wave
import openai

# Load .env keys
load_dotenv()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_REGION")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

stop_threads = False
synthesizer = None

# ✅ Azure TTS
def speak(text):
    global synthesizer
    if stop_threads:
        return
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    speak_task = synthesizer.speak_text_async(text)
    while not speak_task.get().reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        if stop_threads:
            print("🛑 Stopping speech midway")
            synthesizer.stop_speaking_async()
            break
    print(f"🔊 Speaking Done")

# ✅ Deepgram STT (record audio then transcribe)
def listen():
    global stop_threads
    print("🎤 Listening...")
    status.set("Listening...")
    mic_icon.config(text="🎤", fg="green")

    filename = "recorded.wav"
    chunk = 1024
    FORMAT = pyaudio.paInt16
    channels = 1
    rate = 16000
    record_seconds = 5

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)

    frames = []
    for _ in range(0, int(rate / chunk * record_seconds)):
        if stop_threads:
            print("🛑 Listening stopped midway")
            break
        data = stream.read(chunk)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()

    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
    }
    with open(filename, 'rb') as audio:
        response = requests.post(
            "https://api.deepgram.com/v1/listen",
            headers=headers,
            files={"file": audio},
            params={"punctuate": "true", "language": "en-US"}
        )
    os.remove(filename)

    if response.status_code == 200:
        text = response.json().get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
        print(f"🟢 Recognized: {text}")
        status.set(f"Recognized: {text}")
        mic_icon.config(text="")
        return text
    else:
        print("🔴 Deepgram STT error:", response.text)
        status.set("Could not understand audio")
        mic_icon.config(text="")
        return None

# ✅ OpenAI GPT-4o-Nano LLM
def chat_with_openai(user_message):
    if stop_threads:
        print("🛑 LLM call skipped")
        return ""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # GPT-4o includes Nano version by OpenAI
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content.strip()
        print("🤖 OpenAI GPT-4o Reply:", reply)
        return reply
    except Exception as e:
        print(f"🔴 OpenAI API Error: {e}")
        return "Sorry, an error occurred with OpenAI API."

# ✅ Voice Interaction
def handle_voice_interaction():
    global stop_threads
    stop_threads = False

    def interaction():
        try:
            input_text.delete("1.0", tk.END)
            chat_output.delete("1.0", tk.END)
            user_input = listen()
            if stop_threads or user_input is None:
                status.set("Stopped")
                return
            input_text.insert(tk.END, user_input)
            llm_reply = chat_with_openai(user_input)
            if stop_threads or not llm_reply:
                status.set("Stopped")
                return
            chat_output.insert(tk.END, llm_reply)
            speak(llm_reply)
            status.set("Response complete")
        except Exception as e:
            print("🔴 Error:", e)
            speak("An error occurred.")
            status.set(f"Error: {e}")

    threading.Thread(target=interaction, daemon=True).start()

def stop_interaction():
    global stop_threads, synthesizer
    stop_threads = True
    if synthesizer:
        try:
            synthesizer.stop_speaking_async()
            print("🛑 Speech stopped")
        except Exception as e:
            print(f"Error stopping synthesizer: {e}")
    status.set("Stopping...")
    mic_icon.config(text="")
    print("🛑 Stopping interaction")

# ✅ Theme Toggle
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg = "#2c2f33" if dark_mode else "#f2f2f2"
    content_bg = "#23272a" if dark_mode else "white"
    fg = "white" if dark_mode else "black"
    entry_bg = "#2c2f33" if dark_mode else "white"
    entry_fg = "white" if dark_mode else "black"
    window.config(bg=bg)
    header.config(bg="#7289da" if dark_mode else "#007acc")
    main_frame.config(bg=content_bg)
    for widget in main_frame.winfo_children():
        widget.config(bg=content_bg, fg=fg)
    input_text.config(bg=entry_bg, fg=entry_fg, insertbackground=fg)
    chat_output.config(bg=entry_bg, fg=entry_fg, insertbackground=fg)
    mic_button.config(bg="#7289da" if dark_mode else "#007acc", fg="white")
    stop_button.config(bg="#7289da" if dark_mode else "#007acc", fg="white")

# ✅ GUI Setup
window = tk.Tk()
window.title("🧠 Voice Assistant | Deepgram STT + OpenAI GPT-4o-Nano + Azure TTS")
window.geometry("950x620")
window.config(bg="#f2f2f2")
dark_mode = False

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="Voice Assistant | Deepgram STT + OpenAI GPT-4o-Nano + Azure TTS", font=("Arial", 18, "bold"), fg="white", bg="#007acc").pack(pady=10)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")

tk.Label(main_frame, text="Your Question (via Mic):", font=("Arial", 12), bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4, font=("Arial", 11), wrap=tk.WORD)
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial", 14), fg="green", bg="white")
mic_icon.pack()

mic_button = tk.Button(main_frame, text="🎤 Tap to Speak & Get Answer", font=("Arial", 13, "bold"), bg="#007acc", fg="white", command=handle_voice_interaction, padx=20, pady=10)
mic_button.pack(pady=10)

stop_button = tk.Button(main_frame, text="🛑 Stop", font=("Arial", 13, "bold"), bg="#007acc", fg="white", command=stop_interaction, padx=20, pady=10)
stop_button.pack(pady=10)

output_label = tk.Label(main_frame, text="Response:", font=("Arial", 12, "bold"), bg="white")
output_label.pack(anchor="w", pady=(10, 0))
chat_output = tk.Text(main_frame, height=10, font=("Arial", 11), wrap=tk.WORD)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken", anchor="w", font=("Arial", 10), bg="#f2f2f2").pack(fill="x", side="bottom")

theme_button = tk.Button(header, text="Toggle Theme", font=("Arial", 10), bg="#7289da", fg="white", command=toggle_theme)
theme_button.pack(anchor="e", padx=10, pady=5)

window.mainloop()
