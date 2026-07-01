
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import spacy
class HybridRetriever:
    def __init__(self, chroma_client, neo4j_client):
        # takes both clients as input — reuses existing connections
        self.chroma_client = chroma_client
        self.neo4j_client = neo4j_client
        self.nlp = spacy.load("en_core_web_sm")

    def vector_search(self, query, n_results=5):
        # calls ChromaDB search, returns relevant sentences
        return self.chroma_client.search(query, n_results=n_results)

    def extract_entities_from_results(self, vector_results):
        # extracts entity names from vector search results using spaCy
        entities = []
        for result in vector_results['documents'][0]:
            # Assuming each result is a string of text
            doc = self.nlp(result)
            for ent in doc.ents:
                entities.append(ent.text)
        return list(set(entities))  # return unique entities

    def graph_search(self, entities):
        # queries Neo4j for relationships between extracted entities
        # returns list of relationship tuples
        if not entities:
            return []
        with self.neo4j_client.driver.session() as session:
            result = session.run("""
                MATCH (n)-[r]-(m)
                WHERE n.name IN $names
                RETURN n.name, type(r), m.name
            """, names=entities)
            return [(record["n.name"], record["type(r)"], record["m.name"]) 
                    for record in result]
    def retrieve(self, query, n_results=5):
        vector_results = self.vector_search(query, n_results=n_results)
        entities_from_text = self.extract_entities_from_results(vector_results)
        entities_from_query = [ent.text for ent in self.nlp(query).ents]
        entities_from_graph_match = self.find_known_entities_in_query(query)
        all_entities = list(set(entities_from_text + entities_from_query + entities_from_graph_match))
        graph_results = self.graph_search(all_entities)
        return {
            "vector_results": vector_results,
            "graph_results": graph_results
        }

    def format_context(self, retrieval_results):
        context = "RELEVANT TEXT:\n"
        for doc in retrieval_results["vector_results"]["documents"][0]:
            context += f"- {doc[:200]}\n"
        
        context += "\nENTITY RELATIONSHIPS:\n"
        for rel in retrieval_results["graph_results"]:
            context += f"- {rel[0]} {rel[1]} {rel[2]}\n"
        
        return context
    def find_known_entities_in_query(self, query):
        with self.neo4j_client.driver.session() as session:
            result = session.run("""
                MATCH (n) WHERE n.name IS NOT NULL
                RETURN n.name AS name
            """)
            all_names = [record["name"] for record in result]
        query_lower = query.lower()
        return [name for name in all_names if name.lower() in query_lower]
if __name__ == "__main__":
    from src.vector.chroma_client import ChromaClient
    from src.graph.neo4j_client import Neo4jClient

    chroma_client = ChromaClient()
    neo4j_client = Neo4jClient()
    hybrid_retriever = HybridRetriever(chroma_client, neo4j_client)

    query = "Infosys earnings"
    results = hybrid_retriever.retrieve(query, n_results=5)
    context = hybrid_retriever.format_context(results)
    print(context)