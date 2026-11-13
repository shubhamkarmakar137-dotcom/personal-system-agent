import os
import subprocess
import pyautogui
import psutil
import ctypes
import cv2
import base64
import webbrowser
import time
import datetime
import requests

def search_project_files(keyword):
    """Searches all text files in the folder for a keyword and returns their content."""
    allowed_extensions = ['.txt', '.py', '.md', '.json', '.csv']
    found_content = []
    
    try:
        for filename in os.listdir('.'):
            # Only check readable text files to avoid crashing on images or exes
            if os.path.isfile(filename) and any(filename.endswith(ext) for ext in allowed_extensions):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Case-insensitive search
                        if keyword.lower() in content.lower():
                            # We limit the read to 2000 characters per file so it doesn't crash LM Studio
                            found_content.append(f"--- FILE: {filename} ---\n{content[:2000]}") 
                except Exception:
                    pass # Silently skip files that are locked or can't be read
                    
        if found_content:
            return f"Found '{keyword}' in the following files:\n\n" + "\n\n".join(found_content)
        else:
            return f"No files found containing the keyword '{keyword}'."
            
    except Exception as e:
        return f"Error searching files: {str(e)}"
    
def get_weather(location="Howrah"):
    """Gets the current weather for a specified city."""
    try:
        clean_loc = location.strip('"').strip("'")
        
        # We ask the wttr.in service for a simple text format: Condition + Temperature
        url = f"https://wttr.in/{clean_loc}?format=%C,+with+a+temperature+of+%t"
        response = requests.get(url)
        
        if response.status_code == 200:
            return f"The weather in {clean_loc} is {response.text}."
        else:
            return f"Error: Could not check weather for {clean_loc}."
    except Exception as e:
        return f"Error getting weather: {str(e)}"

def get_current_time():
    """Returns the current real-world date and time."""
    now = datetime.datetime.now()
    return now.strftime("The current date and time is %A, %B %d, %Y at %I:%M %p.")

# --- TOOL FUNCTIONS ---
def list_project_files():
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    return f"Files in your folder: {', '.join(files)}"

def read_text_file(filename):
    try:
        clean_path = filename.strip('"').strip("'")
        with open(clean_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading {filename}: {str(e)}"

def analyze_saved_image(filename):
    try:
        clean_path = filename.strip('"').strip("'")
        with open(clean_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        return f"Error: Could not open {filename}."
    
def capture_image():
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    if not ret:
        cam.release()
        return "Error: Could not access webcam.", None
    
    timestamp = int(time.time())
    filename = f"webcam_{timestamp}.jpg"
    
    cv2.imwrite(filename, frame)
    _, buffer = cv2.imencode('.jpg', frame)
    encoded_string = base64.b64encode(buffer).decode('utf-8')
    cam.release()
    return filename, encoded_string

def capture_screen():
    try:
        timestamp = int(time.time())
        filename = f"screenshot_{timestamp}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
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

def open_application(app_name):
    app_map = {
        "calculator": "calc", "excel": "excel", "word": "winword", 
        "powerpoint": "powerpnt", "file explorer": "explorer", 
        "notepad": "notepad", "chrome": "chrome", "browser": "msedge"
    }
    clean_name = app_name.lower().strip()
    target = app_map.get(clean_name, clean_name)
    try:
        if any(target.startswith(prefix) for prefix in ["http://", "https://", "www."]):
            webbrowser.open(target)
            return f"Successfully opened URL: {target}"
        if "win" in os.sys.platform:
            exit_code = os.system(f'start "" "{target}"')
            if exit_code != 0: return f"Error: Could not find or open '{app_name}'."
            return f"Successfully opened {app_name}"
        else:
            subprocess.Popen(["open", "-a", app_name])
            return f"Successfully opened {app_name}"
    except Exception as e:
        return f"Error: {str(e)}"

def delete_file(filename):
    try:
        clean_path = filename.strip('"').strip("'")
        if os.path.exists(clean_path):
            os.remove(clean_path)
            return f"Successfully deleted {filename}."
        else:
            return f"Error: File {filename} not found."
    except Exception as e:
        return f"Error deleting file: {str(e)}"

# --- TOOL LIST FOR GEMMA ---
tools = [
    {"type": "function", "function": {"name": "lock_screen", "description": "Locks the PC"}},
    {"type": "function", "function": {"name": "get_system_stats", "description": "Checks CPU/RAM"}},
    {"type": "function", "function": {"name": "capture_image", "description": "Takes a photo from webcam"}},
    {"type": "function", "function": {"name": "capture_screen", "description": "Captures a screenshot"}},
    {"type": "function", "function": {"name": "list_project_files", "description": "Lists all files"}},
    {"type": "function", "function": {"name": "read_text_file", "description": "Reads a text file.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}}},
    {"type": "function", "function": {"name": "analyze_saved_image", "description": "Analyzes an image.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}}},
    {"type": "function", "function": {"name": "open_application", "description": "Opens Windows apps or URLs.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
    {"type": "function", "function": {"name": "delete_file", "description": "Deletes a specified file.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}}},
    {"type": "function", "function": {"name": "get_current_time", "description": "Gets the current real-world time and date."}},
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Gets the current real-world weather for a specified location.",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "The city to check the weather for."}},
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_project_files",
            "description": "Searches all text-based files in the folder for a specific keyword and reads their contents.",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "The topic, word, or phrase to search for."}},
                "required": ["keyword"]
            }
        }
    }
    ]