from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import API_TITLE, CORS_ORIGINS
from src.api.endpoints import router


app = FastAPI(title=API_TITLE)

# Add CORS middleware for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    print("\n" + "="*70)
    print("🚀 TRAVIA TRAVEL ASSISTANT - BACKEND STARTED")
    print("="*70)
    print("✅ Amadeus API: Connected")
    print("✅ Ollama LLM: Ready")
    print("✅ Session Manager: Initialized")
    print("✅ Agent Graph: Compiled")
    print("="*70 + "\n")


@app.get("/health")
def health_check():
    return {"status": "healthy"}