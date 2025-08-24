# Audit Logging Agent

## Overview
Tracks all system activities and generates audit reports for compliance and monitoring purposes.

## Features

- **Complete Audit Trail**: Logs all system events
- **Real-time Monitoring**: Tracks system activity live
- **Anomaly Detection**: Identifies unusual patterns
- **Report Generation**: Creates detailed audit reports
- **Metrics Dashboard**: Provides system health metrics
- **Performance Tracking**: Monitors agent performance
- **Compliance Reports**: SAMA-compliant audit trails
            

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

from audit_logging.agno_audit_agent import SAMAAuditLoggingAgent

# Initialize agent
agent = SAMAAuditLoggingAgent()

# Log an event
agent.log_event(
    event_type="document-processed",
    event_data={
        "document_id": "doc_123",
        "status": "success"
    }
)

# Generate audit report
report = agent.get_audit_report(
    customer_id="CUSTOMER_001",
    start_date=datetime.now() - timedelta(days=7),
    end_date=datetime.now()
)

print(f"Total Events: {report['total_events']}")
print(f"Report: {report['report_text']}")
            
```

## API Endpoints

The agent exposes the following methods:


- `log_event(event_type, event_data)`: Log audit event
- `get_audit_report(customer_id, start_date, end_date)`: Generate audit report
- `get_compliance_metrics()`: Get real-time metrics
- `monitor_events(duration)`: Monitor system events
        

## Business Value


- **Regulatory Compliance**: Complete audit trail for SAMA
- **Anomaly Detection**: Real-time identification of issues
- **Performance Monitoring**: System health and metrics
- **Forensic Analysis**: Detailed investigation capabilities
        

## Integration Points

- **Input**: System events from all agents
- **Output**: Audit reports, metrics, alerts
- **Events**: audit-log, audit-anomaly

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
python src/copilots/compliance/audit_logging/agno_audit_agent.py
```

## License

Proprietary - SAMA Compliance Co-Pilot
