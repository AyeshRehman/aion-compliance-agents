# AION Compliance Agents - SAMA Compliance Co-Pilot

A comprehensive multi-agent system for Saudi Arabian Monetary Authority (SAMA) compliance, built with the Agno framework and powered by local LLMs.

## 🚀 Features

- **Document Ingestion Agent**: Processes and analyzes compliance documents
- **KYC Validation Agent**: Validates Know Your Customer requirements
- **Compliance Summary Agent**: Generates comprehensive compliance reports
- **Compliance Chat Agent**: Interactive chat interface for compliance queries
- **Audit Logging Agent**: Complete audit trail and monitoring system

## 🏗️ Architecture

### Multi-Agent System
- **5 Specialized Agents** working in coordination
- **Event-driven architecture** using Kafka
- **Local LLM processing** with Ollama (Mistral)
- **Vector database** storage with ChromaDB
- **Real-time caching** with Redis
- **Persistent storage** with SQLite/PostgreSQL

### Technology Stack
- **Framework**: Agno (Agent framework)
- **LLM**: Ollama (Mistral model)
- **Vector DB**: ChromaDB
- **Cache**: Redis
- **Database**: SQLite (development) / PostgreSQL (production)
- **Message Queue**: Kafka (with mock fallback)
- **Language**: Python 3.8+

## 📋 Prerequisites

### Required Services
1. **Ollama** - Local LLM server
2. **Redis** - Caching (optional but recommended)
3. **Kafka** - Event streaming (optional, has mock fallback)

### Python Dependencies
```bash
pip install -r requirements.txt
```

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/AyeshRehman/aion-compliance-agents.git
cd aion-compliance-agents
```

### 2. Set up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install and Configure Ollama
```bash
# Install Ollama (visit https://ollama.ai for your OS)
# Pull the Mistral model
ollama pull mistral

# Start Ollama server
ollama serve
```

### 4. Install Redis (Optional)
```bash
# Windows (via Chocolatey)
choco install redis-64

# macOS (via Homebrew)
brew install redis

# Linux (Ubuntu/Debian)
sudo apt-get install redis-server

# Start Redis
redis-server
```

### 5. Setup Kafka (Optional)
```bash
# Download and start Kafka
# Or use Docker:
docker run -p 9092:9092 apache/kafka
```

## 🚦 Quick Start

### 1. Run Integration Test
```bash
python final_integration_test.py
```

This will test all components and verify the system is working correctly.

### 2. Test Individual Agents

#### Document Ingestion
```bash
cd src/copilots/compliance/document_ingestion
python agno_document_agent_ollama.py
```

#### KYC Validation
```bash
cd src/copilots/compliance/kyc_validation
python agno_kyc_agent.py
```

#### Compliance Summary
```bash
cd src/copilots/compliance/compliance_summary
python agno_summary_agent.py
```

#### Compliance Chat
```bash
cd src/copilots/compliance/compliance_chat
python agno_chat_agent.py
```

#### Audit Logging
```bash
cd src/copilots/compliance/audit_logging
python agno_audit_agent.py
```

## 📊 Monitoring and Reports

### View ChromaDB Documents
```bash
python chromadb_viewer.py
```

### Generate Audit Reports
```bash
python audit_report_viewer.py
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file (optional):
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
REDIS_HOST=localhost
REDIS_PORT=6379
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
DATABASE_URL=sqlite:///./data/compliance.db
```

### Agent Configuration
Edit `src/copilots/compliance/agno_config.py` to customize:
- Model settings
- Database connections
- Kafka topics
- Cache settings

## 📁 Project Structure

```
aion-compliance-agents/
├── src/
│   └── copilots/
│       └── compliance/
│           ├── shared/                 # Shared components
│           │   ├── ollama_agno.py     # Ollama wrapper
│           │   ├── kafka_handler.py   # Event handling
│           │   └── models.py          # Database models
│           ├── document_ingestion/    # Document processing
│           ├── kyc_validation/        # KYC validation
│           ├── compliance_summary/    # Report generation
│           ├── compliance_chat/       # Chat interface
│           └── audit_logging/         # Audit and monitoring
├── data/                             # Data storage
│   ├── chroma_db/                   # Vector database
│   └── compliance.db                # SQLite database
├── test_results/                    # Test outputs
├── audit_reports/                   # Generated reports
├── final_integration_test.py        # Complete system test
├── chromadb_viewer.py              # Database viewer
├── audit_report_viewer.py          # Report viewer
└── requirements.txt                # Dependencies
```

## 🧪 Testing

### Run Full Integration Test
```bash
python final_integration_test.py
```

### Expected Output
```
✅ ALL TESTS PASSED - SYSTEM FULLY OPERATIONAL!
✅ Your SAMA Compliance Co-Pilot is ready for production demo!
```

### Test Results
- Infrastructure: 5/5 components working
- Agents: 5/5 agents operational
- End-to-end workflow: ✅ Complete

## 📝 Usage Examples

### Process a Document
```python
from src.copilots.compliance.document_ingestion.agno_document_agent_ollama import SAMADocumentIngestionAgent

agent = SAMADocumentIngestionAgent()
result = agent.process_document("commercial_registration.pdf", "CUSTOMER_001")
print(f"Document processed: {result['document_id']}")
```

### Validate KYC
```python
from src.copilots.compliance.kyc_validation.agno_kyc_agent import SAMAKYCValidationAgent

kyc_agent = SAMAKYCValidationAgent()
validation = kyc_agent.validate_kyc(document_id, "CUSTOMER_001")
print(f"KYC Status: {validation['validation_status']}")
```

### Generate Compliance Summary
```python
from src.copilots.compliance.compliance_summary.agno_summary_agent import SAMAComplianceSummaryAgent

summary_agent = SAMAComplianceSummaryAgent()
summary = summary_agent.generate_summary("CUSTOMER_001")
print(f"Compliance Status: {summary['compliance_status']}")
```

### Chat Query
```python
from src.copilots.compliance.compliance_chat.agno_chat_agent import SAMAComplianceChatAgent

chat_agent = SAMAComplianceChatAgent()
response = chat_agent.chat("What documents are required for SAMA compliance?", "session_001")
print(response['response'])
```

## 🔍 Troubleshooting

### Common Issues

1. **Ollama Connection Failed**
   ```bash
   # Make sure Ollama is running
   ollama serve
   # Check if model is available
   ollama list
   ```

2. **Character Encoding Errors**
   - Ensure all files use UTF-8 encoding
   - Arabic text support is built-in

3. **Database Issues**
   - System falls back to SQLite automatically
   - Check `./data/compliance.db` exists

4. **Redis Connection Failed**
   - System works without Redis (reduced performance)
   - Start Redis: `redis-server`

### Debug Mode
Enable debug logging in any agent:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python final_integration_test.py`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🏢 About SAMA Compliance

This system helps organizations comply with Saudi Arabian Monetary Authority regulations through:
- Automated document processing
- KYC validation workflows
- Compliance status monitoring
- Comprehensive audit trails
- Real-time reporting capabilities

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the integration test results

## 🎯 Roadmap

- [ ] Web UI interface
- [ ] API endpoints
- [ ] Docker containerization
- [ ] Cloud deployment support
- [ ] Additional document types
- [ ] Multi-language support
- [ ] Advanced analytics dashboard

---

**Built with ❤️ using Agno Framework and Local AI**