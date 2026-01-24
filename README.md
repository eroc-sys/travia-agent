# 🧳 Agentic Travel Assistant

An intelligent travel assistant powered by **LangGraph**, **Ollama (local LLM)**, and the **Amadeus API**.

---

## 🚀 Features

- **Natural Language Understanding** — Ask in plain English  
- **Multi-turn Conversations** — Context-aware follow-ups  
- **Real-time Flight Search** — Powered by Amadeus API  
- **Hotel Recommendations** — Pricing and availability included  
- **Fallback Mechanisms** — Web search when APIs are unavailable  
- **Session Management** — Persistent conversation history  
- **Input Validation** — Protection against injection attacks  

---

## 📋 Prerequisites

- Python **3.9+**
- Ollama installed and running locally
- Amadeus API credentials (free tier supported)

---

## 🔧 Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/agentic-travel-assistant.git
cd agentic-travel-assistant
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up Ollama
```bash
# Install Ollama from https://ollama.ai
# Pull the required model
ollama pull llama3.2:3b
```

### 5. Configure environment variables
```bash

```

create `.env` in root directory and add your credentials:

```env
AMADEUS_CLIENT_ID=your_client_id
AMADEUS_CLIENT_SECRET=your_client_secret
```

---

## 🏃 Running the Application

### Start the FastAPI backend
```bash
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```
### Start the Ollama Server 
```bash
ollama serve 
```

### Start the Streamlit frontend
```bash
streamlit run frontend/streamlit_app.py
```

---

## 🌐 Access the Application

Open your browser and visit:

👉 **http://localhost:8501**

---


## 🧠 Notes

- Ollama ( Local LLM ).
- Amadeus free tier has strict rate limits; fallback logic handles this gracefully.
- Designed for local-first, privacy-friendly execution.
- Supports multi-turn conversations with persistent session memory.
- Streamlit Frontend.

---
