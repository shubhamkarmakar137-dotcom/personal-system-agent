# Gemma_Agent

A modular, voice-enabled Python AI command center that combines local LLM inference via LM Studio with Google Gemini API fallback, GPU-accelerated text-to-speech, and custom system tool calling.

## Features

* **Hybrid Model Routing:** Run models locally using LM Studio (built and tested around Gemma 4) for offline privacy, or route requests to the Gemini API when cloud reasoning is needed.
* **Voice & Local TTS:** Hotkey-triggered voice interaction paired with local, PyTorch-accelerated Silero TTS for low-latency spoken responses.
* **Custom Tool Calling:** Extensible function execution allowing the assistant to run local files, capture the screen, and analyze images.
* **CLI-First Design:** Lightweight terminal interface built in Python without heavy third-party agent frameworks.

## Prerequisites

* Python 3.10+
* [LM Studio](https://lmstudio.ai/) (for local model execution)
* NVIDIA GPU with CUDA support (recommended for local LLM inference and PyTorch TTS)
* A Google Gemini API key (for cloud fallback)

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/shubhamkarmakar137-dotcom/Gemma_Agent.git](https://github.com/shubhamkarmakar137-dotcom/Gemma_Agent.git)
   cd Gemma_Agent
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your `.env` file:**
   Create a `.env` file in the project root and add your key:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

1. Launch **LM Studio**, load your local model, and start the local inference server (`http://localhost:1234/v1`).
2. Start the command center:
   ```bash
   python main9.py
   ```

## License

This project is open-source under the [MIT License](LICENSE).
