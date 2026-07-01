import streamlit as st

st.set_page_config(
    page_title="Graph RAG Engine",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Graph-Based Knowledge RAG Engine")
st.markdown("""
Ask questions about any topic. The system fetches live news, 
builds a knowledge graph, and answers using local AI.
""")

st.sidebar.success("Select a page above to get started.")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Knowledge Graph", "Neo4j", "Active")
with col2:
    st.metric("Vector Store", "ChromaDB", "Active")  
with col3:
    st.metric("Local LLM", "Llama 3.1", "Running")