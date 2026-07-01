import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.title("🧠 Memory")

if "pipeline" not in st.session_state:
    st.warning("Go to the Query page first to initialize the system.")
    st.stop()

pipeline = st.session_state.pipeline

# Section 1 — your code here
# Loop through st.session_state.history, display each Q&A
st.subheader("Recent Q&A (Short-Term Memory)")
if "history" in st.session_state and st.session_state.history:
    for entry in st.session_state.history:
        st.write(f"**Q:** {entry['query']}")
        st.write(f"**A:** {entry['answer']}")
        st.write("---")

# Section 2 — your code here
# Use pipeline.memory_collection.get() to fetch ALL stored documents
# Hint: collection.get() without query_embeddings returns everything
all_memory = pipeline.memory_collection.get()
# returns dict with 'documents', 'ids', 'metadatas' keys
st.subheader("Long-Term Memory")
if all_memory['documents']:
    for doc in all_memory['documents']:
        st.write(f"- {doc}")
else:
    st.write("No long-term memory stored yet.")

# Section 3 — your code here
# Text input + button, call pipeline.recall_long_term(query) and display
st.subheader("Recall Long-Term Memory")
query = st.text_input("Enter a query to recall from long-term memory:")
if st.button("Recall"):
    results = pipeline.recall_long_term(query)
    if results:
        st.write(results)
    else:
        st.write("No relevant documents found.")

# Section 4 — your code here
# Button that calls pipeline.clear_memory()
if st.button("Clear Memory"):
    pipeline.clear_memory()
    st.success("Memory cleared.")