from langchain_ollama import ChatOllama
from src.config.settings import OLLAMA_MODEL, OLLAMA_BASE_URL, OLLAMA_TEMPERATURE


class LLMService:
    def __init__(self):
        self.llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=OLLAMA_TEMPERATURE,
        )
    
    def get_llm(self):
        return self.llm
    
    def get_structured_llm(self, schema):
        return self.llm.with_structured_output(schema)


# Global instance
llm_service = LLMService()