# chromadb_viewer.py
"""
ChromaDB Document Viewer for SAMA Compliance Co-Pilot
View all documents stored in your ChromaDB database
"""

import chromadb
import json
from datetime import datetime

def view_chromadb_documents():
    """View all documents in ChromaDB"""
    
    print("="*60)
    print("CHROMADB DOCUMENT VIEWER")
    print("="*60)
    
    try:
        # Connect to ChromaDB (same path as your agent)
        client = chromadb.PersistentClient(path="./data/chroma_db")
        
        # Get the sama_documents collection
        collection = client.get_collection("sama_documents")
        
        # Get all documents - simple call with no parameters
        results = collection.get()
        
        # Check if results exist and have the expected structure
        if not results or 'ids' not in results:
            print("No documents found. Run some tests first!")
            return
            
        total_docs = len(results['ids'])
        print(f"\nFound {total_docs} documents in ChromaDB\n")
        
        if total_docs == 0:
            print("No documents found. Run some tests first!")
            return
        
        # Display each document
        for i, doc_id in enumerate(results['ids']):
            document = results['documents'][i] if 'documents' in results else "No content"
            metadata = results['metadatas'][i] if 'metadatas' in results else {}
            
            print(f"Document #{i+1}")
            print("-" * 40)
            print(f"ID: {doc_id}")
            print(f"Filename: {metadata.get('filename', 'N/A')}")
            print(f"Customer ID: {metadata.get('customer_id', 'N/A')}")
            print(f"Document Type: {metadata.get('document_type', 'N/A')}")
            print(f"Processed At: {metadata.get('processed_at', 'N/A')}")
            if isinstance(document, str):
                print(f"Content Preview: {document[:500]}...")
                print(f"Content Length: {len(document)} characters")
            print()
        
        # Collection stats
        print("="*40)
        print("COLLECTION STATISTICS")
        print("="*40)
        print(f"Total Documents: {total_docs}")
        print(f"Collection Name: sama_documents")
        print(f"Database Path: ./data/chroma_db")
        
        # Document types breakdown
        if 'metadatas' in results:
            doc_types = {}
            customers = set()
            
            for metadata in results['metadatas']:
                if metadata:
                    doc_type = metadata.get('document_type', 'unknown')
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                    if metadata.get('customer_id'):
                        customers.add(metadata.get('customer_id'))
            
            print(f"\nDocument Types:")
            for doc_type, count in doc_types.items():
                print(f"  - {doc_type}: {count}")
            
            print(f"\nCustomers: {len(customers)}")
            for customer in sorted(customers):
                print(f"  - {customer}")
            
    except Exception as e:
        print(f"Error accessing ChromaDB: {e}")
        print("Make sure ChromaDB path exists: ./data/chroma_db")
        
        # Let's also try to list available collections
        try:
            client = chromadb.PersistentClient(path="./data/chroma_db")
            collections = client.list_collections()
            print(f"\nAvailable collections:")
            for collection in collections:
                print(f"  - {collection.name}")
        except:
            print("Could not list collections either.")
    """View all documents in ChromaDB"""
    
    print("="*60)
    print("CHROMADB DOCUMENT VIEWER")
    print("="*60)
    
    try:
        # Connect to ChromaDB (same path as your agent)
        client = chromadb.PersistentClient(path="./data/chroma_db")
        
        # Get the sama_documents collection
        collection = client.get_collection("sama_documents")
        
        # Get all documents
        results = collection.get(
            results = collection.get()

        )
        
        total_docs = len(results['ids'])
        print(f"\nFound {total_docs} documents in ChromaDB\n")
        
        if total_docs == 0:
            print("No documents found. Run some tests first!")
            return
        
        # Display each document
        for i, (doc_id, document, metadata) in enumerate(zip(
            results['ids'], 
            results['documents'], 
            results['metadatas']
        )):
            print(f"Document #{i+1}")
            print("-" * 40)
            print(f"ID: {doc_id}")
            print(f"Filename: {metadata.get('filename', 'N/A')}")
            print(f"Customer ID: {metadata.get('customer_id', 'N/A')}")
            print(f"Document Type: {metadata.get('document_type', 'N/A')}")
            print(f"Processed At: {metadata.get('processed_at', 'N/A')}")
            print(f"Content Preview: {document[:500]}...")
            print(f"Content Length: {len(document)} characters")
            print()
        
        # Collection stats
        print("="*40)
        print("COLLECTION STATISTICS")
        print("="*40)
        print(f"Total Documents: {total_docs}")
        print(f"Collection Name: sama_documents")
        print(f"Database Path: ./data/chroma_db")
        
        # Document types breakdown
        doc_types = {}
        customers = set()
        
        for metadata in results['metadatas']:
            doc_type = metadata.get('document_type', 'unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            if metadata.get('customer_id'):
                customers.add(metadata.get('customer_id'))
        
        print(f"\nDocument Types:")
        for doc_type, count in doc_types.items():
            print(f"  - {doc_type}: {count}")
        
        print(f"\nCustomers: {len(customers)}")
        for customer in sorted(customers):
            print(f"  - {customer}")
            
    except Exception as e:
        print(f"Error accessing ChromaDB: {e}")
        print("Make sure ChromaDB path exists: ./data/chroma_db")
def view_full_document():
    """View complete content of a specific document"""
    
    try:
        client = chromadb.PersistentClient(path="./data/chroma_db")
        collection = client.get_collection("sama_documents")
        results = collection.get()
        
        if not results or not results.get('ids'):
            print("No documents found!")
            return
        
        # Show list of documents
        print("\nAvailable Documents:")
        print("-" * 50)
        for i, doc_id in enumerate(results['ids']):
            metadata = results['metadatas'][i] if 'metadatas' in results else {}
            filename = metadata.get('filename', 'N/A')
            customer = metadata.get('customer_id', 'N/A')
            doc_type = metadata.get('document_type', 'unknown')
            print(f"{i+1}. {filename} ({customer}) - {doc_type}")
        
        # Get user selection
        while True:
            try:
                choice = input(f"\nEnter document number (1-{len(results['ids'])}): ").strip()
                doc_index = int(choice) - 1
                
                if 0 <= doc_index < len(results['ids']):
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Display full document
        doc_id = results['ids'][doc_index]
        document = results['documents'][doc_index] if 'documents' in results else "No content"
        metadata = results['metadatas'][doc_index] if 'metadatas' in results else {}
        
        print("\n" + "="*80)
        print("FULL DOCUMENT CONTENT")
        print("="*80)
        print(f"Document ID: {doc_id}")
        print(f"Filename: {metadata.get('filename', 'N/A')}")
        print(f"Customer ID: {metadata.get('customer_id', 'N/A')}")
        print(f"Document Type: {metadata.get('document_type', 'N/A')}")
        print(f"Processed At: {metadata.get('processed_at', 'N/A')}")
        print("-" * 80)
        print("CONTENT:")
        print("-" * 80)
        print(document)
        print("="*80)
        
    except Exception as e:
        print(f"Error viewing document: {e}")
def search_documents(query_text):
    """Search documents by content"""
    
    print(f"\nSearching for: '{query_text}'")
    print("-" * 40)
    
    try:
        client = chromadb.PersistentClient(path="./data/chroma_db")
        collection = client.get_collection("sama_documents")
        
        # Perform similarity search
        results = collection.query(
            query_texts=[query_text],
            n_results=5,  # Top 5 most similar
            results = collection.get()

        )
        
        if not results['ids'][0]:
            print("No matching documents found.")
            return
        
        print(f"Found {len(results['ids'][0])} matching documents:\n")
        
        for i, (doc_id, document, metadata, distance) in enumerate(zip(
            results['ids'][0],
            results['documents'][0], 
            results['metadatas'][0],
            results['distances'][0]
        )):
            print(f"Match #{i+1} (Similarity: {1-distance:.3f})")
            print(f"ID: {doc_id}")
            print(f"File: {metadata.get('filename', 'N/A')}")
            print(f"Type: {metadata.get('document_type', 'N/A')}")
            print(f"Content: {document[:150]}...")
            print()
            
    except Exception as e:
        print(f"Search error: {e}")

def export_documents():
    """Export all documents to JSON file"""
    
    try:
        client = chromadb.PersistentClient(path="./data/chroma_db")
        collection = client.get_collection("sama_documents")
        
        results = collection.get(
            results = collection.get()

        )
        
        # Create export data
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_documents": len(results['ids']),
            "documents": []
        }
        
        for doc_id, document, metadata in zip(
            results['ids'], 
            results['documents'], 
            results['metadatas']
        ):
            export_data["documents"].append({
                "id": doc_id,
                "content": document,
                "metadata": metadata
            })
        
        # Save to file
        filename = f"chromadb_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"Documents exported to: {filename}")
        print(f"Total documents: {export_data['total_documents']}")
        
    except Exception as e:
        print(f"Export error: {e}")

def main():
    """Main menu"""
    
    while True:
        print("\n" + "="*60)
        print("CHROMADB DOCUMENT VIEWER - MAIN MENU")
        print("="*60)
        print("1. View All Documents (Summary)")
        print("2. View Full Document Content")
        print("3. Search Documents")
        print("4. Export Documents to JSON")
        print("5. Exit")
        print()
        
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == '1':
            view_chromadb_documents()
        
        elif choice == '2':
            view_full_document()
        
        elif choice == '3':
            query = input("Enter search query: ").strip()
            if query:
                search_documents(query)
        
        elif choice == '4':
            export_documents()
        
        elif choice == '5':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")
if __name__ == "__main__":
    main()