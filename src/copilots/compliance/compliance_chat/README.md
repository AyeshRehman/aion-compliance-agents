# Compliance Chat Agent

## Overview
Interactive Q&A agent that provides compliance guidance using RAG (Retrieval Augmented Generation) technology.

## Features

- **Natural Language Interface**: Chat-based compliance assistance
- **RAG Technology**: Retrieves relevant documents for context
- **Vector Search**: Uses ChromaDB for semantic search
- **Context-Aware**: Maintains conversation history
- **Source Attribution**: Provides sources for answers
- **Multi-Session**: Supports multiple concurrent sessions
- **Intelligent Responses**: AI-powered answer generation
            

## Technical Architecture

### Technologies Used
- **Agno Framework**: Agent orchestration and management
- **Ollama**: Local LLM for AI-powered analysis
- **ChromaDB**: Vector database for document storage and RAG
- **Redis**: Caching layer for performance optimization
- **PostgreSQL/SQLite**: Persistent storage for records
- **Kafka/Mock Events**: Event-driven communication

## Usage

```python

from compliance_chat.agno_chat_agent import SAMAComplianceChatAgent

# Initialize agent
agent = SAMAComplianceChatAgent()

# Ask a question
result = agent.chat(
    user_query="What documents are required for SAMA compliance?",
    session_id="session_001"
)

# Get response
print(f"Answer: {result['response']}")
print(f"Sources: {result['sources']}")
print(f"Confidence: {result['confidence']}")
            
```

## API Endpoints

The agent exposes the following methods:


- `chat(user_query, session_id)`: Process user query with RAG
- `get_session_summary(session_id)`: Get chat session summary
- `end_session(session_id)`: Close chat session
        

## Business Value


- **24/7 Support**: Always available compliance assistance
- **Knowledge Access**: Instant access to compliance information
- **Training Tool**: Helps staff understand SAMA requirements
- **Consistency**: Uniform responses to compliance queries
        

## Integration Points

- **Input**: Natural language queries
- **Output**: Natural language responses with sources
- **Events**: chat-interaction

## Configuration

Environment variables:
- `OLLAMA_MODEL`: LLM model to use (default: mistral)
- `REDIS_HOST`: Redis server host (default: localhost)
- `DATABASE_URL`: Database connection string

## Performance Metrics

- Average processing time: < 2 seconds
- Concurrent processing: Supported
- Caching: Enabled via Redis
- Scalability: Horizontal scaling supported

## Error Handling

The agent implements comprehensive error handling:
- Graceful fallback when services unavailable
- Detailed error logging
- Automatic retry mechanisms
- Memory storage fallback

## Testing

Run the test suite:
```bash
python src/copilots/compliance/compliance_chat/agno_chat_agent.py
```

## License

Proprietary - SAMA Compliance Co-Pilot
