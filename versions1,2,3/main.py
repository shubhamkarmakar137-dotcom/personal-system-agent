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

# --- CONFIGURATION ---
USE_VOICE_INPUT = False  # Toggle Microphone
USE_VOICE_RESPONSE = True  # Toggle Speaker
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

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
    """Captures a frame from the webcam and saves it."""
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    if not ret:
        cam.release()
        return "Error: Could not access webcam."
    
    cv2.imwrite("agent_view.jpg", frame)
    _, buffer = cv2.imencode('.jpg', frame)
    encoded_string = base64.b64encode(buffer).decode('utf-8')
    cam.release()
    return encoded_string

def capture_screen():
    """Captures a screenshot of the current screen and saves it."""
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save("screen_capture.png")
        return "Screenshot saved as screen_capture.png"
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
    }
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

# --- AGENT BRAIN ---
def run_agent(user_prompt):
    messages = [
        {
            "role": "system", 
            "content": "You are Gemma, a local AI assistant. You have the power to open local apps and web URLs using the 'open_application' tool. If a user provides a link, use that tool to open it."
        },
        {"role": "user", "content": user_prompt}
    ]
    
    response = client.chat.completions.create(model="local-model", messages=messages, tools=tools)
    msg = response.choices[0].message
    messages.append(msg)

    if msg.tool_calls:
        for tool in msg.tool_calls:
            name = tool.function.name
            args = json.loads(tool.function.arguments) if tool.function.arguments else {}
            print(f"--- [Action]: {name} ---")
            
            tool_res = ""
            if name == "lock_screen": tool_res = lock_screen()
            elif name == "get_system_stats": tool_res = get_system_stats()
            elif name == "open_application": tool_res = open_application(args.get("app_name"))
            elif name == "capture_screen": tool_res = capture_screen()
            elif name == "list_project_files": tool_res = list_project_files()
            elif name == "read_text_file": tool_res = read_text_file(args.get("filename"))
            elif name == "capture_image":
                b64_img = capture_image()
                v_msg = [{"role": "user", "content": [{"type": "text", "text": "Describe this photo."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}]
                v_res = client.chat.completions.create(model="local-model", messages=v_msg)
                tool_res = v_res.choices[0].message.content
            elif name == "analyze_saved_image":
                b64_img = analyze_saved_image(args.get("filename"))
                if "Error" in b64_img: tool_res = b64_img
                else:
                    v_msg = [{"role": "user", "content": [{"type": "text", "text": f"Analyze {args.get('filename')}"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}]
                    v_res = client.chat.completions.create(model="local-model", messages=v_msg)
                    tool_res = v_res.choices[0].message.content
            
            messages.append({"role": "tool", "tool_call_id": tool.id, "name": name, "content": tool_res})

        final = client.chat.completions.create(model="local-model", messages=messages)
        answer = final.choices[0].message.content
    else:
        answer = msg.content

    print(f"Gemma: {answer}")
    speak(answer)

# --- MAIN LOOP ---
if __name__ == "__main__":  
    print("\n" + "="*30)
    print("LOCAL COMMAND CENTER LOADED")
    print("Type 'command/' for help.")
    print("="*30)

    while True:
        prompt = get_voice_input() if USE_VOICE_INPUT else input("\nUser: ")
        if prompt:
            if prompt.strip().lower() == "command/":
                display_help_menu()
                continue
            if any(term in prompt.lower() for term in ["stop", "exit"]): break
            run_agent(prompt)