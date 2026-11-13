import json
import speech_recognition as sr
from gtts import gTTS
import pygame
import os
import re
import winsound
from openai import OpenAI
import keyboard
import tkinter as tk
from tkinter import simpledialog
import threading
import queue
import winsound

# 👉 THIS IS THE MAGIC CONNECTION:
from my_tools1 import *

# --- CONFIGURATION ---
USE_VOICE_INPUT = False  
USE_VOICE_RESPONSE = True  
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio", timeout=45.0)

# 👉 NEW: The exact word needed to end the conversation
STOP_WORD = "terminate"

# --- INITIALIZE VOICE ENGINE ---
pygame.mixer.init()

# --- VOICE LOGIC ---
def get_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n[Listening...]")
        # Plays a short, pleasant beep to let you know the mic is hot!
        winsound.Beep(800, 200) 
        
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
        except: return None

def speak(text):
    if USE_VOICE_RESPONSE:
        try:
            # Clean the text of markdown/emojis so the audio engine doesn't stutter
            clean_text = re.sub(r'[^\x00-\x7F]+', '', text) 
            clean_text = clean_text.replace('*', '').replace('#', '').replace('_', '')
            
            # If the AI accidentally returns a blank message, don't try to speak it
            if not clean_text.strip(): 
                return
            
            # 1. Ask Google to turn the text into natural speech
            tts = gTTS(text=clean_text, lang='en')
            
            # 2. Save it as a temporary audio file
            temp_file = "temp_response.mp3"
            tts.save(temp_file)
            
            # 3. Play the audio file reliably
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            # 4. Wait for the audio to finish playing before moving on
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            # 5. Clean up the temp file
            pygame.mixer.music.unload()
            os.remove(temp_file)
            
        except Exception as e:
            print(f"\n[Audio Engine Error: {e}]")

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
                elif name == "get_current_time": tool_res = get_current_time()
                elif name == "capture_screen": tool_res = capture_screen()
                elif name == "get_weather": tool_res = get_weather(args.get("location"))
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
    """Triggered by the voice hotkey. Loops until the stop word is spoken."""
    print("\n[Voice Mode Activated]")
    speak("I am listening.")  # Tells your mom it's ready!
    
    while True:
        prompt = get_voice_input()
        
        if prompt:
            # Check if the user said ONLY the exact stop word (case-insensitive)
            if prompt.strip().lower() == STOP_WORD:
                print(f"\n[Stop Word '{STOP_WORD}' Detected. Going to sleep.]")
                speak("Goodbye.")
                break  # This breaks the loop and puts the agent back to sleep
            
            # If it's a normal command, run the agent
            run_agent(prompt)
            
            # After Gemma finishes talking, it loops back to the top automatically!
            print("\n[Continuing conversation... waiting for next command or stop word.]")

def wake_agent_text():
    print("\n[Text Active] Awaiting manual input...")
    prompt = get_text_input()
    if prompt: run_agent(prompt)

def trigger_voice(): task_queue.put("voice")
def trigger_text(): task_queue.put("text")

if __name__ == "__main__":  
    print("\n" + "="*40)
    print("🚀 LOCAL COMMAND CENTER: ACTIVE")
    print("🎤 Voice Hotkey: 'F9'")
    print("⌨️  Text Hotkey: 'F10'")
    print(f"🛑 Say exactly '{STOP_WORD}' to end a voice conversation.")
    print("Hold 'esc' to safely shut down.")
    print("="*40)

    # The new, finger-friendly hotkeys
    keyboard.add_hotkey('f9', trigger_voice)
    keyboard.add_hotkey('f10', trigger_text)

    while True:
        if keyboard.is_pressed('esc'):
            print("\nShutting down Command Center.")
            break
        
        try:
            task = task_queue.get(timeout=0.1)
            if task == "text": wake_agent_text()
            elif task == "voice": wake_agent_voice()
        except queue.Empty: pass