import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import chromadb
from sentence_transformers import SentenceTransformer
import nltk
nltk.download('punkt_tab', quiet=True)
from nltk.tokenize import sent_tokenize
from bs4 import BeautifulSoup


class ChromaClient:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./data/chroma")
        self.model = SentenceTransformer('all-mpnet-base-v2')
        self.collection = self.client.get_or_create_collection(name="news_articles")
    def clean_text(self, text):
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text().strip()

    def split_into_sentences(self, text):
        return sent_tokenize(text)

    def generate_embedding(self, text):
        return self.model.encode(text).tolist()

    def store_article(self, processed_article):
        content = self.clean_text(processed_article.get("content", ""))
        sentences = self.split_into_sentences(content)
        for i, sentence in enumerate(sentences):
            if len(sentence.strip()) < 10:
                continue
            embedding = self.generate_embedding(sentence)
            unique_id = f"{processed_article.get('title', '')}_{i}"[:100]
            self.collection.add(
                documents=[sentence],
                embeddings=[embedding],
                metadatas=[{
                    "title": processed_article.get("title", ""),
                    "source": processed_article.get("source", ""),
                    "date": processed_article.get("date", "")
                }],
                ids=[unique_id]
            )

    def search(self, query, n_results=5):
        query_embedding = self.generate_embedding(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return results

    def close(self):
        pass  # PersistentClient auto-saves

if __name__ == "__main__":
    from src.ingestion.loader import fetch_multiple_queries
    from src.ingestion.extractor import process_article

    client = ChromaClient()
    articles = fetch_multiple_queries(["Infosys earnings"])
    for article in articles:
        processed = process_article(article)
        client.store_article(processed)
        print(f"Stored: {article['title']}")

    results = client.search("Infosys quarterly results", n_results=3)
    for doc in results['documents'][0]:
        print(f"Match: {doc[:100]}")