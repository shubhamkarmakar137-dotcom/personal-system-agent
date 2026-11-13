import os
import subprocess
import pyautogui
import psutil
from openai import OpenAI
import json
import ctypes
import speech_recognition as sr
import pyttsx3
import cv2
import base64
import webbrowser
import keyboard
import tkinter as tk
from tkinter import simpledialog
import threading
import queue
import time
# --- CONFIGURATION ---
USE_VOICE_INPUT = False  # Toggle Microphone
USE_VOICE_RESPONSE = True  # Toggle Speaker
client = OpenAI(
    base_url="http://localhost:1234/v1", 
    api_key="lm-studio", 
    timeout=45.0  # Forces a timeout after 45 seconds
)

# --- INITIALIZE VOICE ENGINE ---
engine = pyttsx3.init()
engine.setProperty('rate', 180)

# --- TOOL FUNCTIONS ---
def list_project_files():
    """Lists all files in the current project folder."""
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    return f"Files in your folder: {', '.join(files)}"

def read_text_file(filename):
    """Reads the content of a text or code file."""
    try:
        clean_path = filename.strip('"').strip("'")
        with open(clean_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading {filename}: {str(e)}"

def analyze_saved_image(filename):
    """Encodes a saved image file to base64 for Gemma to see."""
    try:
        clean_path = filename.strip('"').strip("'")
        with open(clean_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        return f"Error: Could not open {filename}."
    
def capture_image():
    """Captures a frame from the webcam and saves it with a unique name."""
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    if not ret:
        cam.release()
        return "Error: Could not access webcam.", None
    
    # Create a unique filename using the current time
    timestamp = int(time.time())
    filename = f"webcam_{timestamp}.jpg"
    
    cv2.imwrite(filename, frame)
    _, buffer = cv2.imencode('.jpg', frame)
    encoded_string = base64.b64encode(buffer).decode('utf-8')
    cam.release()
    
    # Return BOTH the filename and the image data
    return filename, encoded_string

def capture_screen():
    """Captures a screenshot of the current screen and saves it."""
    try:
        # Create a unique filename using the current time
        timestamp = int(time.time())
        filename = f"screenshot_{timestamp}.png"
        
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        
        # Tell the AI exactly what the new file is called so it remembers!
        return f"Screenshot saved as {filename}"
    except Exception as e:
        return f"Error capturing screen: {str(e)}"

def lock_screen():
    if "win" in os.sys.platform:
        ctypes.windll.user32.LockWorkStation()
        return "Computer locked."
    return "Not supported on this OS."

def get_system_stats():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    return f"CPU is at {cpu} percent and RAM is at {ram} percent."

def display_help_menu():
    """Prints a beautiful list of all available agent powers."""
    menu = """
==================================================
        🤖 GEMMA AGENT - COMMAND CHEAT SHEET
==================================================
📁 FILES:
   - "list my project files" (Shows everything in this folder)
   - "read [filename]"      (Reads text/code files)
   - "analyze [filename]"   (Looks at a saved image)

📸 VISION & SYSTEM:
   - "take a picture"       (Webcam capture)
   - "check system stats"   (CPU/RAM health)
   - "lock my computer"     (Security lock)

🚀 APPLICATIONS:
   - "open [app name]"      (Chrome, Excel, Calc, etc.)

💡 TIP: You can speak these or type them!
==================================================
    """
    print(menu)

def open_application(app_name):
    """Opens a system application or a web URL."""
    app_map = {
        "calculator": "calc", "excel": "excel", "word": "winword", 
        "powerpoint": "powerpnt", "file explorer": "explorer", 
        "notepad": "notepad", "chrome": "chrome", "browser": "msedge",
        "copilot": "ms-copilot:" 
    }
    clean_name = app_name.lower().strip()
    target = app_map.get(clean_name, clean_name)
    
    try:
        # Check if the target is a web URL
        if any(target.startswith(prefix) for prefix in ["http://", "https://", "www."]):
            webbrowser.open(target)
            return f"Successfully opened URL: {target}"
            
        # Handle local applications
        if "win" in os.sys.platform:
            # Using 'start "" "target"' ensures that the shell handles 
            # paths or commands with spaces and special characters correctly.
            exit_code = os.system(f'start "" "{target}"')
            if exit_code != 0:
                return f"Error: Could not find or open '{app_name}'."
            return f"Successfully opened {app_name}"
        else:
            # macOS/Linux fallback
            subprocess.Popen(["open", "-a", app_name])
            return f"Successfully opened {app_name}"
    except Exception as e:
        return f"Error: {str(e)}"

# --- TOOL LIST FOR GEMMA ---
tools = [
    {"type": "function", "function": {"name": "lock_screen", "description": "Locks the PC"}},
    {"type": "function", "function": {"name": "get_system_stats", "description": "Checks CPU/RAM"}},
    {"type": "function", "function": {"name": "capture_image", "description": "Takes a photo from webcam"}},
    {"type": "function", "function": {"name": "capture_screen", "description": "Captures a screenshot of the current screen"}},
    {"type": "function", "function": {"name": "list_project_files", "description": "Lists all files in project folder"}},
    {
        "type": "function",
        "function": {
            "name": "read_text_file",
            "description": "Reads a text or code file.",
            "parameters": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_saved_image",
            "description": "Analyzes an existing image file.",
            "parameters": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application", 
            "description": "Opens Windows apps or web URLs in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {"app_name": {"type": "string"}},
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Deletes a specified file from the computer.",
            "parameters": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
                "required": ["filename"]
            }
        }
    },
]


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

def delete_file(filename):
    """Deletes a file from the system."""
    try:
        clean_path = filename.strip('"').strip("'")
        if os.path.exists(clean_path):
            os.remove(clean_path)
            return f"Successfully deleted {filename}."
        else:
            return f"Error: File {filename} not found."
    except Exception as e:
        return f"Error deleting file: {str(e)}"
# --- MEMORY SETUP ---
MAX_MEMORY_LENGTH = 15  # Keeps the last 15 messages so LM Studio doesn't crash from context overload

conversation_history = [
    {
        "role": "system", 
        "content": "You are Gemma, a local AI assistant. You can open apps, read files, and see the screen. ALWAYS reply with a short text response confirming what you did after using a tool."
    }
]
# --- AGENT BRAIN ---
# --- AGENT BRAIN ---
def run_agent(user_prompt):
    global conversation_history
    
    # 1. Add your new prompt to the memory bank
    conversation_history.append({"role": "user", "content": user_prompt})
    
    try:
        # 2. Send the WHOLE memory bank to LM Studio
        response = client.chat.completions.create(model="local-model", messages=conversation_history, tools=tools)
        msg = response.choices[0].message
        
        # 3. Save the agent's thought process/tool call to memory
        conversation_history.append(msg)

        if msg.tool_calls:
            for tool in msg.tool_calls:
                name = tool.function.name
                args = json.loads(tool.function.arguments) if tool.function.arguments else {}
                print(f"--- [Action]: {name} ---")
                
                tool_res = ""
                
                # ---> YOUR TOOL LOGIC <---
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
                        tool_res = filename  # This will hold the error message if the webcam fails
                    else:
                        v_msg = [{"role": "user", "content": [{"type": "text", "text": "Describe this photo."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}]
                        v_res = client.chat.completions.create(model="local-model", messages=v_msg)
                        description = v_res.choices[0].message.content
                        
                        # Save BOTH the filename and the visual description into the agent's memory
                        tool_res = f"Image saved as {filename}. Description of what you see: {description}"
                elif name == "analyze_saved_image":
                    b64_img = analyze_saved_image(args.get("filename"))
                    if "Error" in b64_img: tool_res = b64_img
                    else:
                        v_msg = [{"role": "user", "content": [{"type": "text", "text": f"Analyze {args.get('filename')}"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}]
                        v_res = client.chat.completions.create(model="local-model", messages=v_msg)
                        tool_res = v_res.choices[0].message.content
                
                # 4. Save the tool's result to memory
                conversation_history.append({"role": "tool", "tool_call_id": tool.id, "name": name, "content": str(tool_res)})

            # 5. Let the agent read the tool results and form a final answer
            final = client.chat.completions.create(model="local-model", messages=conversation_history)
            answer = final.choices[0].message.content
            
            # 6. Save the final spoken answer to memory
            conversation_history.append({"role": "assistant", "content": answer})
            
        else:
            answer = msg.content

        print(f"Gemma: {answer}")
        speak(answer)

        # --- MEMORY TRIMMER ---
        # If memory gets too long, keep the system prompt [0] and the most recent messages
        if len(conversation_history) > MAX_MEMORY_LENGTH:
            conversation_history = [conversation_history[0]] + conversation_history[-(MAX_MEMORY_LENGTH-1):]

    except Exception as e:
        print(f"\n[System Error]: LM Studio took too long or dropped connection. ({e})")
        speak("I lost connection to the local server.")
        
        # If it crashes, remove the last user prompt so it doesn't get stuck in a bad loop
        if conversation_history[-1]["role"] == "user":
            conversation_history.pop()
# --- MAIN LOOP UI FIX ---

# 1. Initialize the hidden UI engine ONCE at the top level
gui_root = tk.Tk()
gui_root.withdraw()

# Create a message queue to talk to the main thread safely
task_queue = queue.Queue()

def get_text_input():
    """Reuses the existing UI engine to show the popup safely."""
    gui_root.attributes('-topmost', True)  
    prompt = simpledialog.askstring("Command Center", "Type your command:", parent=gui_root)
    return prompt

def wake_agent_voice():
    """Triggered by the voice hotkey."""
    print("\n[Mic Active] Listening...")
    prompt = get_voice_input()
    if prompt: 
        run_agent(prompt)

def wake_agent_text():
    """Triggered by the text hotkey."""
    print("\n[Text Active] Awaiting manual input...")
    prompt = get_text_input()
    if prompt: 
        run_agent(prompt)

def trigger_voice():
    """Sends a signal to the main thread to start voice mode."""
    task_queue.put("voice")

def trigger_text():
    """Sends a signal to the main thread to start text mode."""
    task_queue.put("text")
if __name__ == "__main__":  
    print("\n" + "="*40)
    print("🚀 LOCAL COMMAND CENTER: ACTIVE")
    print("🎤 Voice Hotkey: 'ctrl+alt+space'")
    print("⌨️  Text Hotkey: 'ctrl+alt+t'")
    print("Hold 'esc' to safely shut down.")
    print("="*40)

    # The hotkeys now just drop a message into the queue
    keyboard.add_hotkey('ctrl+alt+space', trigger_voice)
    keyboard.add_hotkey('ctrl+alt+t', trigger_text)

    # Main thread loop: constantly checks the queue for tasks
    while True:
        if keyboard.is_pressed('esc'):
            print("\nShutting down Command Center.")
            break
        
        try:
            # Check the queue (timeout allows it to keep checking for 'esc')
            task = task_queue.get(timeout=0.1)
            
            # Execute safely in the MAIN thread
            if task == "text":
                wake_agent_text()
            elif task == "voice":
                wake_agent_voice()
                
        except queue.Empty:
            # Queue is empty, just loop again
            pass