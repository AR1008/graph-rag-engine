import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.pipeline import Pipeline

st.title("🧠 Graph-Based Knowledge RAG Engine")

if "pipeline" not in st.session_state:
    with st.spinner("Loading models... (first time only)"):
        st.session_state.pipeline = Pipeline()

if "messages" not in st.session_state:
    st.session_state.messages = []  # each: {"role", "content", "sources"?, "graph"?}

pipeline = st.session_state.pipeline

# Replay full conversation on every rerun
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander("Sources & Graph Relationships"):
                st.markdown("**Sources:**")
                for doc in msg["sources"]:
                    st.write(f"- {doc[:200]}")
                st.markdown("**Graph Relationships:**")
                for rel in msg["graph"]:
                    st.write(f"- {rel[0]} **{rel[1]}** {rel[2]}")

prompt = st.chat_input("Ask a question about any topic")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Researching and thinking..."):
            retrieval_results = pipeline.retriever.retrieve(prompt)
            answer = pipeline.run(prompt)
        st.write(answer)
        sources = retrieval_results["vector_results"]["documents"][0]
        graph = retrieval_results["graph_results"]
        with st.expander("Sources & Graph Relationships"):
            st.markdown("**Sources:**")
            for doc in sources:
                st.write(f"- {doc[:200]}")
            st.markdown("**Graph Relationships:**")
            for rel in graph:
                st.write(f"- {rel[0]} **{rel[1]}** {rel[2]}")

    st.session_state.messages.append({
        "role": "assistant", "content": answer, "sources": sources, "graph": graph
    })

with st.sidebar:
    st.write(f"Messages in this conversation: {len(st.session_state.messages)}")
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()