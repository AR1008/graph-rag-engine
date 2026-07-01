import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv()
import ollama


class OllamaClient:
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "llama3.1")
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = ollama.Client(host=ollama_host)
    
    def build_prompt(self, prompt, context):
        return f"""You are a financial knowledge assistant. 
    Use ONLY the information in the CONTEXT below to answer. 
    Do not use any outside knowledge you may already have.
    If the context does not contain enough information to answer confidently, say so explicitly — do not guess or fill gaps from memory.

    CONTEXT:
    {context}

    QUESTION:
    {prompt}

    ANSWER:"""
    def generate(self, prompt, context):
        full_prompt = self.build_prompt(prompt, context)
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}]
        )
        return response['message']['content']
if __name__ == "__main__":
    client = OllamaClient()
    context = "The capital of France is Paris."
    prompt = "What is the capital of France?"
    response = client.generate(prompt, context)
    print("Generated Response:", response)