import os
from dotenv import load_dotenv

load_dotenv()

# Amadeus Configuration
AMADEUS_CLIENT_ID = os.environ.get("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.environ.get("AMADEUS_CLIENT_SECRET")

# LLM Configuration
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_TEMPERATURE = 0

# API Configuration
API_TITLE = "Agentic Travel Assistant (Local LLM)"
API_PORT = 8000

# CORS Configuration
CORS_ORIGINS = ["*"]

# Currency Conversion
EUR_TO_INR = 107.19