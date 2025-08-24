# Compliance Summary Agent

## Overview
Generates comprehensive compliance summaries and reports for customers based on their documents and validations.

## Features

- **Automated Summaries**: Generates compliance reports automatically
- **AI-Powered Insights**: Uses LLM for executive summaries
- **Compliance Scoring**: Calculates overall compliance scores
- **Issue Aggregation**: Consolidates all compliance issues
- **Recommendations**: Provides next steps for compliance
- **Multi-Source**: Aggregates data from multiple agents
- **Caching**: Stores summaries for quick retrieval
            

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

from compliance_summary.agno_summary_agent import SAMAComplianceSummaryAgent

# Initialize agent
agent = SAMAComplianceSummaryAgent()

# Generate summary
result = agent.generate_summary(customer_id="CUSTOMER_001")

# View summary
print(f"Status: {result['compliance_status']}")
print(f"Score: {result['overall_compliance_score']:.2%}")
print(f"Summary: {result['summary_text']}")
            
```

## API Endpoints

The agent exposes the following methods:


- `generate_summary(customer_id)`: Generate compliance summary for customer
- `update_summary(customer_id)`: Update existing summary
- `get_summary(customer_id)`: Retrieve customer summary
        

## Business Value


- **Executive Visibility**: Real-time compliance dashboards
- **Decision Support**: AI-generated insights and recommendations
- **Time Savings**: Instant summaries vs. manual compilation
- **Proactive Compliance**: Identifies issues before audits
        

## Integration Points

- **Input**: Customer IDs, validation results
- **Output**: Compliance reports, scores, summaries
- **Events**: compliance-summary-generated

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
python src/copilots/compliance/compliance_summary/agno_summary_agent.py
```

## License

Proprietary - SAMA Compliance Co-Pilot
