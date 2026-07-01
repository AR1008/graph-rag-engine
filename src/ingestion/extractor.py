import spacy
import sys
import os
from flair.data import Sentence
from flair.models import SequenceTagger
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.ingestion.loader import fetch_multiple_queries
nlp = spacy.load("en_core_web_sm")
flair_tagger = SequenceTagger.load("ner")
from bs4 import BeautifulSoup
from src.ingestion.entity_linker import lookup_entity_type


def clean_html(text):
    return BeautifulSoup(text, "html.parser").get_text()

def extract_entities(text):
    """
    Extract named entities from the given text using spaCy.
    """
    doc = nlp(text)
    flair_sentence = Sentence(text)
    flair_tagger.predict(flair_sentence)
    flair_entities = flair_sentence.get_spans("ner")
    # In extract_entities — before finalizing the organizations list, run each org through lookup_entity_type() and move anything that comes back "LOCATION" into the locations list instead.
    locations = []
    organizations = []
    for org in [ent.text for ent in flair_entities if ent.tag == "ORG"]:
        if lookup_entity_type(org) == "LOCATION":
            locations.append(org)
        else:
            organizations.append(org)
    return {
        "persons": [ent.text for ent in flair_entities if ent.tag == "PER"],
        "organizations": organizations,
        "locations": locations,
        "money": [ent.text for ent in doc.ents if ent.label_ == "MONEY"],
        "dates": [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    }

def extract_relationships(text):
    """
    Extract relationships between entities in the given text using keyword matching.
    Returns a list of tuples (entity1, relationship_type, entity2).
    """
    relationships = []
    doc = nlp(text)
    
    # Define some keywords for relationship extraction
    PERSON_TO_ORG_RELATIONS = {
        "ceo": "CEO_OF",
        "chief executive": "CEO_OF",
        "chairman": "CHAIRMAN_OF",
        "founder": "FOUNDER_OF",
        "co-founder": "FOUNDER_OF",
        "founded": "FOUNDER_OF",
        "leads": "LEADS",
        "appointed": "APPOINTED_AS",
        "named as": "APPOINTED_AS",
        "steps down": "STEPPED_DOWN_FROM",
        "resigns": "STEPPED_DOWN_FROM",
        "resigned": "STEPPED_DOWN_FROM",
    }

    ORG_TO_ORG_RELATIONS = {
        "acquired": "ACQUIRED",
        "acquisition": "ACQUIRED",
        "merged": "MERGED_WITH",
        "merger": "MERGED_WITH",
        "partnered": "PARTNERED_WITH",
        "partnership": "PARTNERED_WITH",
        "invested": "INVESTED_IN",
        "investment": "INVESTED_IN",
        "collaborated": "COLLABORATED_WITH",
    }
    

    # Tag each sentence with Flair once, reusing the spans for both the
    # org pre-resolution pass and the relationship extraction pass below.
    sentence_spans = []
    for sent in doc.sents:
        flair_sentence = Sentence(sent.text)
        flair_tagger.predict(flair_sentence)
        sentence_spans.append((sent.text.lower(), flair_sentence.get_spans("ner")))

    org_candidates = {ent.text for _, spans in sentence_spans for ent in spans if ent.tag == "ORG"}
    confirmed_orgs = {name for name in org_candidates if lookup_entity_type(name) == "ORGANIZATION"}

    for sent_text, sent_entities in sentence_spans:
        for keyword, relation in PERSON_TO_ORG_RELATIONS.items():
            if keyword in sent_text:
                persons = [ent.text for ent in sent_entities if ent.tag == "PER"]
                orgs = [ent.text for ent in sent_entities if ent.tag == "ORG" and ent.text in confirmed_orgs]
                if persons and orgs:
                    relationships.append((persons[0], relation, orgs[0]))

        for keyword, relation in ORG_TO_ORG_RELATIONS.items():
            if keyword in sent_text:
                orgs = [ent.text for ent in sent_entities if ent.tag == "ORG" and ent.text in confirmed_orgs]
                if len(orgs) >= 2:
                    relationships.append((orgs[0], relation, orgs[1]))
    return relationships

def process_article(article):
    content = clean_html(article.get("content", ""))
    entities = extract_entities(content)
    relationships = extract_relationships(content)
    article["entities"] = entities
    article["relationships"] = relationships
    return article

if __name__ == "__main__":
    queries = sys.argv[1:] if len(sys.argv) > 1 else ["technology news", "stock market India"]
    articles = fetch_multiple_queries(queries)
    for article in articles:
        processed_article = process_article(article)
        print(f"Title: {processed_article['title']}")
        print(f"Source: {processed_article['source']}")
        print(f"Date: {processed_article['date']}")
        print(f"Entities: {processed_article['entities']}")
        print(f"Relationships: {processed_article['relationships']}")
        print("-" * 80)

