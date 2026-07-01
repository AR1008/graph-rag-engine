import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from neo4j import GraphDatabase 
from src import neo4j_uri, neo4j_username, neo4j_password

class Neo4jClient:
    def __init__(self) :          # connect to Neo4j
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

    def create_node(self, label, properties):    # merge a single node
        if not properties.get("name") or len(properties["name"]) < 2 or properties["name"].replace(",","").replace(".","").isnumeric():
            return
        with self.driver.session() as session:
            session.run(
                f"MERGE (n:{label} {{name: $name}}) SET n += $props",
                name=properties.get("name", ""),
                props=properties
            )

    def create_relationship(self, node1, rel_type, node2):  # connect two nodes
        with self.driver.session() as session:
            session.run(
                f"MATCH (a {{name: $name1}}) MATCH (b {{name: $name2}}) "
                f"MERGE (a)-[:{rel_type}]->(b)",
                name1=node1, name2=node2
            )
    def store_article(self, processed_article):  # store everything from one article
            label_map = {
            "persons": "Person",
            "organizations": "Company", 
            "locations": "Location",
            "money": "Money"
                }

            for category, names in processed_article["entities"].items():
                neo4j_label = label_map.get(category)
                if not neo4j_label:
                    continue
                for name in names:
                    self.create_node(neo4j_label, {"name": name})
                for rel in processed_article["relationships"]:
                    self.create_relationship(rel[0], rel[1], rel[2])
            self.create_node("Article", {
                "name": processed_article["title"],
                "source": processed_article["source"],
                "date": processed_article["date"]
            })

            for category, names in processed_article["entities"].items():
                neo4j_label = label_map.get(category)
                if not neo4j_label:
                    continue
                for name in names:
                    self.create_relationship(name, "MENTIONED_IN", processed_article["title"])
    def close(self):              # close connection
        self.driver.close()
if __name__ == "__main__":
    from src.ingestion.loader import fetch_multiple_queries
    from src.ingestion.extractor import process_article
    create_neo4j_client = Neo4jClient()
    articles = fetch_multiple_queries(["Infosys earnings"])
    for article in articles:
        processed_article = process_article(article)
        create_neo4j_client.store_article(processed_article)
    create_neo4j_client.close()
    print("Articles stored in Neo4j successfully.")