import json
import speech_recognition as sr
import pyttsx3
from openai import OpenAI
import keyboard
import tkinter as tk
from tkinter import simpledialog
import threading
import queue

# 👉 THIS IS THE MAGIC CONNECTION:
from my_tools import *

# --- CONFIGURATION ---
USE_VOICE_INPUT = False  
USE_VOICE_RESPONSE = True  
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio", timeout=45.0)

# --- INITIALIZE VOICE ENGINE ---
engine = pyttsx3.init()
engine.setProperty('rate', 180)

# --- VOICE LOGIC ---
def get_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n[Listening...]")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
        except: return None

def speak(text):
    if USE_VOICE_RESPONSE:
        engine.say(text)
        engine.runAndWait()

# --- MEMORY SETUP ---
MAX_MEMORY_LENGTH = 15  
conversation_history = [
    {
        "role": "system", 
        "content": "You are Gemma, a local AI assistant. You can open apps, read files, and see the screen. ALWAYS reply with a short text response confirming what you did after using a tool."
    }
]

# --- AGENT BRAIN ---
def run_agent(user_prompt):
    global conversation_history
    conversation_history.append({"role": "user", "content": user_prompt})
    
    try:
        response = client.chat.completions.create(model="local-model", messages=conversation_history, tools=tools)
        msg = response.choices[0].message
        conversation_history.append(msg)

        if msg.tool_calls:
            for tool in msg.tool_calls:
                name = tool.function.name
                args = json.loads(tool.function.arguments) if tool.function.arguments else {}
                print(f"--- [Action]: {name} ---")
                
                tool_res = ""
                
                # These tools are pulled perfectly from my_tools.py!
                if name == "lock_screen": tool_res = lock_screen()
                elif name == "get_system_stats": tool_res = get_system_stats()
                elif name == "open_application": tool_res = open_application(args.get("app_name"))
                elif name == "list_project_files": tool_res = list_project_files()
                elif name == "read_text_file": tool_res = read_text_file(args.get("filename"))
                elif name == "capture_screen": tool_res = capture_screen()
                elif name == "delete_file": tool_res = delete_file(args.get("filename"))
                elif name == "capture_image":
                    filename, b64_img = capture_image()
                    if b64_img is None:
                        tool_res = filename  
                    else:
                        v_msg = [{"role": "user", "content": [{"type": "text", "text": "Describe this photo."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}]
                        v_res = client.chat.completions.create(model="local-model", messages=v_msg)
                        description = v_res.choices[0].message.content
                        tool_res = f"Image saved as {filename}. Description of what you see: {description}"
                elif name == "analyze_saved_image":
                    b64_img = analyze_saved_image(args.get("filename"))
                    if "Error" in b64_img: tool_res = b64_img
                    else:
                        v_msg = [{"role": "user", "content": [{"type": "text", "text": f"Analyze {args.get('filename')}"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}]
                        v_res = client.chat.completions.create(model="local-model", messages=v_msg)
                        tool_res = v_res.choices[0].message.content
                
                conversation_history.append({"role": "tool", "tool_call_id": tool.id, "name": name, "content": str(tool_res)})

            final = client.chat.completions.create(model="local-model", messages=conversation_history)
            answer = final.choices[0].message.content
            conversation_history.append({"role": "assistant", "content": answer})
        else:
            answer = msg.content

        print(f"Gemma: {answer}")
        speak(answer)

        if len(conversation_history) > MAX_MEMORY_LENGTH:
            conversation_history = [conversation_history[0]] + conversation_history[-(MAX_MEMORY_LENGTH-1):]

    except Exception as e:
        print(f"\n[System Error]: LM Studio took too long or dropped connection. ({e})")
        speak("I lost connection to the local server.")
        if conversation_history[-1]["role"] == "user":
            conversation_history.pop()

# --- MAIN LOOP UI FIX ---
gui_root = tk.Tk()
gui_root.withdraw()
task_queue = queue.Queue()

def get_text_input():
    gui_root.attributes('-topmost', True)  
    prompt = simpledialog.askstring("Command Center", "Type your command:", parent=gui_root)
    return prompt

def wake_agent_voice():
    print("\n[Mic Active] Listening...")
    prompt = get_voice_input()
    if prompt: run_agent(prompt)

def wake_agent_text():
    print("\n[Text Active] Awaiting manual input...")
    prompt = get_text_input()
    if prompt: run_agent(prompt)

def trigger_voice(): task_queue.put("voice")
def trigger_text(): task_queue.put("text")

if __name__ == "__main__":  
    print("\n" + "="*40)
    print("🚀 LOCAL COMMAND CENTER: ACTIVE")
    print("🎤 Voice Hotkey: 'ctrl+alt+space'")
    print("⌨️  Text Hotkey: 'ctrl+alt+t'")
    print("Hold 'esc' to safely shut down.")
    print("="*40)

    keyboard.add_hotkey('ctrl+alt+space', trigger_voice)
    keyboard.add_hotkey('ctrl+alt+t', trigger_text)

    while True:
        if keyboard.is_pressed('esc'):
            print("\nShutting down Command Center.")
            break
        
        try:
            task = task_queue.get(timeout=0.1)
            if task == "text": wake_agent_text()
            elif task == "voice": wake_agent_voice()
        except queue.Empty: pass