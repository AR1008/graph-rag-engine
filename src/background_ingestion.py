import sys, os, json
from datetime import datetime
from unittest import result
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.schedulers.blocking import BlockingScheduler
from src.vector.chroma_client import ChromaClient
from src.graph.neo4j_client import Neo4jClient
from src.ingestion.loader import fetch_multiple_queries
from src.ingestion.extractor import process_article

SEEN_FILE = os.path.join(os.path.dirname(__file__), "seen_articles.json")
DEFAULT_TOPICS = [
    "Infosys", "TCS", "Wipro", "HCLTech", "Tech Mahindra",
    "Reliance Industries", "HDFC Bank", "ICICI Bank",
    "Zomato", "Swiggy", "Razorpay", "CRED",
    "Anthropic AI", "OpenAI", "Google DeepMind",
    "Nvidia AI chips", "Indian startup funding",
    "NSE BSE stock market India", "RBI monetary policy"
]
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen_set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen_set), f)

def get_dynamic_topics(chroma_client):
    # TODO: implement this yourself.
    # 1. Fetch documents from chroma_client.client.get_or_create_collection("conversation_memory")
    #    using .get(limit=50) to avoid pulling unbounded history
    # 2. Each document looks like "Q: <question>\nA: <answer>" (see pipeline.py's remember_long_term)
    #    Split each document on "\n", find the line starting with "Q: ", strip that prefix to get just the question
    # 3. Collect into a set() to dedupe identical past questions
    # 4. If the resulting set is empty (cold start), return DEFAULT_TOPICS instead
    # 5. Return as a list
    result = chroma_client.client.get_or_create_collection("conversation_memory").get(limit=50)
    documents = result["documents"]
    questions = set()
    for doc in documents:
        lines = doc.split("\n")
        for line in lines:
            if line.startswith("Q: "):
                questions.add(line[3:].strip())
    if not questions:
        return DEFAULT_TOPICS
    return list(questions)

def ingest_job():
    print(f"[{datetime.now()}] Starting ingestion cycle...")
    chroma = ChromaClient()
    neo4j = Neo4jClient()
    seen = load_seen()
    topics = get_dynamic_topics(chroma)
    print(f"Monitoring topics: {topics}")

    # TODO: implement this yourself.
    # 1. articles = fetch_multiple_queries(topics)
    # 2. Loop through articles. For each one:
    #    - skip if article['url'] is already in `seen`
    #    - otherwise: process_article(article), then neo4j.store_article(...), then chroma.store_article(...)
    #    - add article['url'] to `seen`
    # 3. Track a count of how many NEW articles you actually ingested this cycle
    # 4. save_seen(seen) at the end
    # 5. print(f"Ingested {count} new articles this cycle.")
    articles = fetch_multiple_queries(topics)
    new_count = 0
    for article in articles:    
        if article['url'] in seen:
            continue
        processed = process_article(article)
        neo4j.store_article(processed)
        chroma.store_article(processed)
        seen.add(article['url'])
        new_count += 1
    save_seen(seen)
    print(f"Ingested {new_count} new articles this cycle.")
    pass

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(ingest_job, 'interval', hours=6, next_run_time=datetime.now())
    print("Background ingestion service started. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Service stopped.")