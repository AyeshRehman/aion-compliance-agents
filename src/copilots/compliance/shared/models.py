# src/copilots/compliance/shared/models.py
"""
Database models for SAMA Compliance Co-Pilot
Fixed version - no reserved words
"""

from sqlalchemy import create_engine, Column, String, Boolean, Integer, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import json

# Database configuration - support multiple connection methods
def get_database_url():
    """Get database URL with fallback options"""
    
    # Try environment variable first
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    
    # Try PostgreSQL with different passwords
    postgres_configs = [
        "postgresql://postgres:postgres@127.0.0.1:5432/compliance",
        "postgresql://postgres:postgres@localhost:5432/compliance",
        "postgresql://postgres:password@localhost:5432/compliance"
    ]
    
    for config in postgres_configs:
        try:
            from sqlalchemy import create_engine
            engine = create_engine(config)
            engine.connect().close()
            print(f"Using PostgreSQL: {config}")
            return config
        except:
            continue
    
    # Fallback to SQLite for testing
    print("Warning: PostgreSQL not available, using SQLite for testing")
    os.makedirs("./data", exist_ok=True)
    return "sqlite:///./data/compliance.db"

# Get database URL
DATABASE_URL = get_database_url()

# Create base class for models
Base = declarative_base()

# Create engine and session
engine = None
SessionLocal = None

def init_database():
    """Initialize database connection"""
    global engine, SessionLocal
    try:
        # Create engine with connection pooling
        engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True  # Verify connections before using
        )
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        print(f"Database initialized: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

# ============================================================================
# MODELS FOR ALL 5 AGENTS
# ============================================================================

class Document(Base):
    """
    Model for Document Ingestion Agent
    Stores all processed documents
    """
    __tablename__ = "documents"
    
    # Primary key
    id = Column(String, primary_key=True, index=True)
    
    # Document information
    filename = Column(String, nullable=False)
    file_type = Column(String)
    file_path = Column(String)
    
    # Customer information
    customer_id = Column(String, index=True)
    
    # Content
    extracted_text = Column(Text)
    text_length = Column(Integer)
    
    # Processing information
    processed = Column(Boolean, default=False)
    processing_status = Column(String, default='pending')
    processed_at = Column(DateTime, default=datetime.utcnow)
    
    # Analysis results from Document Ingestion Agent
    document_type = Column(String)
    confidence_score = Column(Float)
    compliance_score = Column(Float)
    quality_score = Column(Float)
    sama_compliant = Column(Boolean, default=False)
    
    # AI analysis results
    ai_enhanced = Column(Boolean, default=False)
    ai_analysis = Column(Text)  # JSON string of AI analysis
    
    # Issues and recommendations (stored as JSON strings)
    issues = Column(Text)  # JSON array as string
    recommendations = Column(Text)  # JSON array as string
    
    # Vector storage reference
    vector_id = Column(String)  # Reference to ChromaDB/Pinecone
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KYCValidation(Base):
    """
    Model for KYC Validation Agent
    Stores KYC validation results
    """
    __tablename__ = "kyc_validations"
    
    # Primary key
    id = Column(String, primary_key=True, index=True)
    
    # References
    document_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    
    # Validation results
    validation_status = Column(String)  # passed, failed, pending
    validation_score = Column(Float)
    
    # Specific KYC checks
    identity_verified = Column(Boolean, default=False)
    address_verified = Column(Boolean, default=False)
    business_verified = Column(Boolean, default=False)
    
    # Document type being validated
    document_type = Column(String)
    
    # Detailed validation results
    validation_details = Column(Text)  # JSON string with detailed results
    
    # AI validation results
    ai_validated = Column(Boolean, default=False)
    ai_confidence = Column(Float)
    ai_notes = Column(Text)
    
    # Issues and recommendations
    issues = Column(Text)  # JSON array as string
    recommendations = Column(Text)  # JSON array as string
    
    # Timestamps
    validated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class ComplianceSummary(Base):
    """
    Model for Compliance Summary Agent
    Stores compliance summaries for customers
    """
    __tablename__ = "compliance_summaries"
    
    # Primary key
    id = Column(String, primary_key=True, index=True)
    
    # Customer reference
    customer_id = Column(String, unique=True, index=True)
    
    # Summary statistics
    total_documents = Column(Integer, default=0)
    validated_documents = Column(Integer, default=0)
    compliant_documents = Column(Integer, default=0)
    
    # Compliance scores
    overall_compliance_score = Column(Float)
    kyc_score = Column(Float)
    document_score = Column(Float)
    
    # Status
    compliance_status = Column(String)  # compliant, partially_compliant, non_compliant
    
    # AI-generated summary
    summary_text = Column(Text)
    executive_summary = Column(Text)
    
    # Detailed breakdown
    document_breakdown = Column(Text)  # JSON with document type counts
    validation_breakdown = Column(Text)  # JSON with validation results
    
    # Issues and recommendations
    issues_summary = Column(Text)  # JSON array of all issues
    recommendations_summary = Column(Text)  # JSON array of all recommendations
    
    # Next steps
    next_steps = Column(Text)
    
    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatSession(Base):
    """
    Model for Compliance Chat Agent
    Stores chat sessions and interactions
    """
    __tablename__ = "chat_sessions"
    
    # Primary key
    id = Column(String, primary_key=True, index=True)
    
    # Session information
    session_id = Column(String, unique=True, index=True)
    customer_id = Column(String, index=True)
    
    # Session metadata
    start_time = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_queries = Column(Integer, default=0)
    
    # Session status
    status = Column(String, default='active')  # active, closed, expired
    
    # Conversation history (stored as JSON)
    conversation_history = Column(Text)  # JSON array of messages
    
    # Context used (references to documents)
    documents_referenced = Column(Text)  # JSON array of document IDs
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatInteraction(Base):
    """
    Model for individual chat interactions
    Part of Compliance Chat Agent
    """
    __tablename__ = "chat_interactions"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Session reference
    session_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    
    # Query and response
    user_query = Column(Text)
    agent_response = Column(Text)
    
    # RAG information
    documents_retrieved = Column(Text)  # JSON array of retrieved docs
    confidence_score = Column(Float)
    used_rag = Column(Boolean, default=False)
    
    # Response metadata (renamed from 'metadata' to avoid reserved word)
    response_time_ms = Column(Integer)  # Response time in milliseconds
    tokens_used = Column(Integer)
    
    # Timestamp
    interaction_time = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """
    Model for Audit Logging Agent
    Stores all system audit logs
    """
    __tablename__ = "audit_logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Event information
    event_type = Column(String, nullable=False, index=True)
    event_id = Column(String)
    
    # Actor information
    agent_name = Column(String, index=True)
    customer_id = Column(String, index=True)
    user_id = Column(String)  # If triggered by a user
    
    # Event details
    action = Column(String, nullable=False)
    resource_type = Column(String)  # document, validation, summary, etc.
    resource_id = Column(String)  # ID of the resource affected
    
    # Event data
    details = Column(Text)  # JSON string with full event details
    event_metadata = Column(Text)  # JSON string with additional metadata (renamed from 'metadata')
    
    # Status and results
    status = Column(String, index=True)  # success, failure, warning
    error_message = Column(Text)
    
    # Performance metrics
    duration_ms = Column(Integer)  # How long the operation took
    
    # Anomaly detection
    is_anomaly = Column(Boolean, default=False)
    anomaly_details = Column(Text)
    
    # Timestamp
    occurred_at = Column(DateTime, default=datetime.utcnow, index=True)


class SystemMetrics(Base):
    """
    Model for system-wide metrics
    Used by Audit Logging Agent
    """
    __tablename__ = "system_metrics"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Metric information
    metric_name = Column(String, index=True)
    metric_value = Column(Float)
    metric_unit = Column(String)
    
    # Context
    agent_name = Column(String)
    metric_type = Column(String)  # performance, quality, compliance
    
    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def create_tables():
    """Create all tables in database"""
    if not init_database():
        print("Cannot create tables - database not initialized")
        return False
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("All database tables created successfully")
        print(f"Tables created: {', '.join(Base.metadata.tables.keys())}")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

def drop_tables():
    """Drop all tables (use with caution)"""
    if not init_database():
        return False
    
    try:
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped")
        return True
    except Exception as e:
        print(f"Error dropping tables: {e}")
        return False

def get_database_session():
    """Get database session"""
    if not SessionLocal:
        init_database()
    
    if SessionLocal:
        return SessionLocal()
    return None

def test_database_connection():
    """Test database connection"""
    try:
        if not init_database():
            return False
        
        # Try to execute a simple query
        session = get_database_session()
        if session:
            # Use SQLAlchemy's text() for raw SQL
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            session.close()
            return True
        return False
    except Exception as e:
        print(f"Database test failed: {e}")
        return False

def get_database_stats():
    """Get database statistics"""
    stats = {}
    
    try:
        session = get_database_session()
        if session:
            stats['documents'] = session.query(Document).count()
            stats['kyc_validations'] = session.query(KYCValidation).count()
            stats['compliance_summaries'] = session.query(ComplianceSummary).count()
            stats['chat_sessions'] = session.query(ChatSession).count()
            stats['audit_logs'] = session.query(AuditLog).count()
            session.close()
    except:
        stats = {'error': 'Could not retrieve stats'}
    
    return stats


# Initialize database on import
if __name__ != "__main__":
    init_database()

# Test script
if __name__ == "__main__":
    print("Testing Database Models")
    print("=" * 60)
    
    # Test connection
    if test_database_connection():
        print("✓ Database connection successful")
        
        # Create tables
        if create_tables():
            print("✓ All tables created")
            
            # Get stats
            stats = get_database_stats()
            print("\nDatabase Statistics:")
            for table, count in stats.items():
                print(f"  {table}: {count}")
    else:
        print("✗ Database connection failed")
        print("Using SQLite fallback for testing")