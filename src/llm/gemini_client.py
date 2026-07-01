import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv()
from google import genai

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "gemini-1.5-flash"

    def build_prompt(self, prompt, context):
        return f"""You are a financial knowledge assistant. 
Use the following context to answer the question accurately.

CONTEXT:
{context}

QUESTION:
{prompt}

ANSWER:"""

    def build_verify_prompt(self, ollama_answer, context):
        return f"""You are a fact-checker. Review this answer against the context.

CONTEXT:
{context}

ANSWER TO VERIFY:
{ollama_answer}

If the answer is accurate and complete, return it as-is.
If it has errors or missing information, provide a corrected version.
Return only the final answer, no explanation."""

    def generate(self, prompt, context):
        full_prompt = self.build_prompt(prompt, context)
        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt
        )
        return response.text

    def verify(self, ollama_answer, context):
        full_prompt = self.build_verify_prompt(ollama_answer, context)
        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt
        )
        return response.text

if __name__ == "__main__":
    client = GeminiClient()
    context = "The capital of France is Paris."
    prompt = "What is the capital of France?"
    response = client.generate(prompt, context)
    print("Generated Response:", response)