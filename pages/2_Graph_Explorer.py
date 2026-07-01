import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyvis.network import Network

st.title("🕸️ Graph Explorer")

if "pipeline" not in st.session_state:
    st.warning("Go to the Query page first to initialize the system.")
    st.stop()

neo4j_driver = st.session_state.pipeline.neo4j.driver

filter_text = st.text_input("Filter by entity name (optional)")
limit = st.slider("Max relationships to show", 10, 200, 50)

if st.button("Load Graph"):
    with neo4j_driver.session() as session:
        if filter_text:
            result = session.run("""
                MATCH (n)-[r]->(m) 
                WHERE n.name CONTAINS $filter OR m.name CONTAINS $filter
                RETURN n.name AS source, labels(n)[0] AS source_label, 
                       type(r) AS rel, m.name AS target, labels(m)[0] AS target_label
                LIMIT $limit
            """, filter=filter_text, limit=limit)
        else:
            result = session.run("""
                MATCH (n)-[r]->(m) 
                RETURN n.name AS source, labels(n)[0] AS source_label,
                       type(r) AS rel, m.name AS target, labels(m)[0] AS target_label
                LIMIT $limit
            """, limit=limit)
        
        records = list(result)

    if not records:
        st.info("No relationships found. Try a different filter or run page 1 first to populate the graph.")
    else:
        net = Network(height="600px", width="100%", bgcolor="#ffffff", directed=True)
        
        color_map = {"Company": "lightblue", "Person": "lightgreen", "Location": "orange", 
                     "Money": "pink", "Article": "lightgray"}
        
        for record in records:
            net.add_node(record["source"], label=record["source"], 
                         color=color_map.get(record["source_label"], "gray"))
            net.add_node(record["target"], label=record["target"],
                         color=color_map.get(record["target_label"], "gray"))
            net.add_edge(record["source"], record["target"], label=record["rel"])
        
        net.save_graph("graph.html")
        with open("graph.html", "r") as f:
            st.components.v1.html(f.read(), height=600)
        
        st.caption(f"Showing {len(records)} relationships")