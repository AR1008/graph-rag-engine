import os
import sys
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from src.llm.ollama_client import OllamaClient
from src.llm.gemini_client import GeminiClient
from src.retrieval.hybrid_retriever import HybridRetriever
from src.vector.chroma_client import ChromaClient
from src.graph.neo4j_client import Neo4jClient
import uuid

class Pipeline:
    def __init__(self):
        self.conversation_history = []
        self.chroma = ChromaClient()
        self.neo4j = Neo4jClient()
        self.retriever = HybridRetriever(self.chroma, self.neo4j)
        self.ollama = OllamaClient()
        self.gemini = GeminiClient()
        self.memory_collection = self.chroma.client.get_or_create_collection("conversation_memory")

    def remember_short_term(self, query, answer): # add to conversation history
        self.conversation_history.append((query, answer))
        self.conversation_history = self.conversation_history[-3:]

    def remember_long_term(self, query, answer):
        embedding = self.chroma.generate_embedding(f"{query} {answer}")
        self.memory_collection.add(
            documents=[f"Q: {query}\nA: {answer}"],
            embeddings=[embedding],
            ids=[str(uuid.uuid4())]
        )

    def recall_long_term(self, query):
        embedding = self.chroma.generate_embedding(query)
        results = self.memory_collection.query(
            query_embeddings=[embedding],
            n_results=3
        )
        if results['documents'][0]:
            return "PAST CONVERSATIONS:\n" + "\n".join(results['documents'][0])
        return ""


    def run(self, query):
        # 1. Recall long-term memory
        past_context = self.recall_long_term(query)
        
        # 2. Build conversation context from short-term memory
        history_context = self.format_history()
        
        # 3. Retrieve from hybrid retriever
        retrieval_results = self.retriever.retrieve(query)
        knowledge_context = self.retriever.format_context(retrieval_results)
        
        # 4. Combine all context
        full_context = f"""PAST RELEVANT CONVERSATIONS:
        {past_context if past_context else "None"}

        THIS SESSION'S RECENT CONVERSATION:
        {history_context if history_context else "None"}

        RELEVANT NEWS AND KNOWLEDGE:
        {knowledge_context}"""
        
        # 5. Ollama generates answer
        ollama_answer = self.ollama.generate(query, full_context)
        
        # 6. Gemini verifies (skip if quota exceeded)
        try:
            final_answer = self.gemini.verify(ollama_answer, full_context)
        except Exception as e:
            print(f"Gemini unavailable ({e.__class__.__name__}), using Ollama answer.")
            final_answer = ollama_answer
            
        # 7. Store in memory
        self.remember_short_term(query, final_answer)
        self.remember_long_term(query, final_answer)
        
        return final_answer

    def clear_memory(self):      # reset conversation history
        self.conversation_history = []

    def format_history(self):
        recent = self.conversation_history[-3:]
        return "\n".join([f"Q: {h[0]}\nA: {h[1]}" for h in recent])
if __name__ == "__main__":
    pipeline = Pipeline()
    while True:
        query = input("\nAsk a question (or 'quit' to exit): ")
        if query.lower() == 'quit':
            break
        answer = pipeline.run(query)
        print(f"\nAnswer: {answer}")