from dotenv import load_dotenv
import os   
load_dotenv()  # Load environment variables from .env file
api_key = os.getenv("GEMINI_API_KEY")
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
ollama_model = os.getenv("OLLAMA_MODEL")
gemini_model = os.getenv("GEMINI_MODEL")
if __name__ == "__main__":
    print(f"Gemini Key: {api_key[:4]}...")
    print(f"Neo4j URI: {neo4j_uri}")
    print(f"Ollama Model: {ollama_model}")
    print(f"Gemini Model: {gemini_model}")