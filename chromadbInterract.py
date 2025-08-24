import streamlit as st
import chromadb

# Connect to Chroma persistent DB
client = chromadb.PersistentClient(path="./data/chroma_db")

st.title("ChromaDB Explorer")

# List collections
collections = client.list_collections()
selected = st.selectbox("Choose a collection", [c.name for c in collections])

if selected:
    collection = client.get_collection(selected)
    results = collection.get(include=["documents", "metadatas"])

    st.write("📊 Total items:", collection.count())
    st.dataframe({
        "ID": results["ids"],
        "Document": results["documents"],
        "Metadata": results["metadatas"]
    })
