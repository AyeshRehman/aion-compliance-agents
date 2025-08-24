# src/copilots/compliance/audit_logging/agno_audit_agent.py
"""
Audit Logging Agent for SAMA Compliance
Tracks all system activities for compliance audit trails
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Agno framework
from agno.agent import Agent

# Import shared components
from shared.ollama_agno import OllamaForAgno
from shared.kafka_handler import KafkaHandler
from shared.models import AuditLog, get_database_session, create_tables

# Import Redis for real-time monitoring
import redis

# Logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SAMAAuditLoggingAgent(Agent):
    """
    Audit Logging Agent
    
    This agent:
    1. Monitors all Kafka events
    2. Logs all agent activities
    3. Tracks compliance operations
    4. Generates audit reports
    5. Ensures traceability
    """
    
    def __init__(self):
        """Initialize Audit Logging Agent"""
        
        print("Starting Audit Logging Agent...")
        
        # Initialize Ollama LLM for report generation
        try:
            self.llm = OllamaForAgno(
                model="mistral",
                base_url="http://localhost:11434"
            )
        except Exception as e:
            print(f"Warning: Ollama not initialized: {e}")
            self.llm = None
        
        # Initialize Redis for real-time metrics
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            self.redis_client.ping()
            print("Redis connected for metrics")
        except:
            self.redis_client = None
            print("Redis not available")
        
        # Initialize base Agent
        super().__init__(
            name="AuditLoggingAgent",
            model=self.llm,
            description="Tracks all compliance activities for audit"
        )
        
        # Initialize Kafka
        self.kafka_handler = KafkaHandler()
        
        # Initialize database
        self.db_session = None
        try:
            create_tables()
            self.db_session = get_database_session()
            print("Database connected for audit logs")
        except:
            print("Database not available - using memory")
            self.memory_logs = []
        
        # Topics to monitor
        self.monitored_topics = [
            "document-processed",
            "kyc-validation-requested",
            "kyc-validation-completed",
            "compliance-summary-requested",
            "compliance-summary-generated",
            "chat-interaction",
            "audit-log"
        ]
        
        # Event counters
        self.event_counters = {}
        
        print("Audit Logging Agent ready!")
    
    def log_event(self, event_type: str, event_data: Dict) -> Dict[str, Any]:
        """
        Log an audit event
        
        Args:
            event_type: Type of event
            event_data: Event details
            
        Returns:
            Log entry dictionary
        """
        
        # Create audit log entry
        log_entry = {
            "event_type": event_type,
            "event_id": event_data.get("event_id", ""),
            "agent_name": event_data.get("agent_name", "unknown"),
            "customer_id": event_data.get("customer_id", ""),
            "action": event_data.get("action", event_type),
            "details": json.dumps(event_data),
            "status": event_data.get("status", "success"),
            "occurred_at": datetime.now()
        }
        
        # Store in database
        self._store_audit_log(log_entry)
        
        # Update metrics
        self._update_metrics(event_type)
        
        # Check for anomalies
        anomalies = self._detect_anomalies(event_type, event_data)
        if anomalies:
            self._handle_anomalies(anomalies)
        
        return {
            "logged": True,
            "event_type": event_type,
            "timestamp": log_entry["occurred_at"].isoformat()
        }
    
    def get_audit_report(self, customer_id: Optional[str] = None, 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> Dict:
        """
        Generate audit report
        
        Args:
            customer_id: Filter by customer (optional)
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            Audit report dictionary
        """
        
        print(f"Generating audit report...")
        
        # Default date range (last 24 hours)
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=1)
        
        # Retrieve logs
        logs = self._get_audit_logs(customer_id, start_date, end_date)
        
        # Analyze logs
        analysis = self._analyze_logs(logs)
        
        # Generate report text
        report_text = self._generate_report_text(analysis, customer_id, start_date, end_date)
        
        return {
            "report_id": f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "customer_id": customer_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_events": len(logs),
            "event_breakdown": analysis["event_counts"],
            "agent_activity": analysis["agent_counts"],
            "status_summary": analysis["status_counts"],
            "report_text": report_text,
            "generated_at": datetime.now().isoformat()
        }
    
    def get_compliance_metrics(self) -> Dict:
        """
        Get real-time compliance metrics
        
        Returns:
            Metrics dictionary
        """
        
        metrics = {
            "total_events_today": 0,
            "success_rate": 0.0,
            "active_agents": [],
            "recent_failures": [],
            "system_health": "healthy"
        }
        
        if self.redis_client:
            try:
                # Get today's events
                today = datetime.now().strftime('%Y%m%d')
                
                # Get all event types
                for topic in self.monitored_topics:
                    key = f"audit:daily:{today}:{topic}"
                    count = self.redis_client.get(key)
                    if count:
                        metrics["total_events_today"] += int(count)
                
                # Calculate success rate
                success_key = f"audit:daily:{today}:success"
                failure_key = f"audit:daily:{today}:failure"
                
                success_count = int(self.redis_client.get(success_key) or 0)
                failure_count = int(self.redis_client.get(failure_key) or 0)
                
                total = success_count + failure_count
                if total > 0:
                    metrics["success_rate"] = success_count / total
                
                # Get recent failures
                failure_keys = self.redis_client.keys("audit:failure:*")
                metrics["recent_failures"] = len(failure_keys)
                
                # Determine system health
                if metrics["success_rate"] < 0.5:
                    metrics["system_health"] = "critical"
                elif metrics["success_rate"] < 0.8:
                    metrics["system_health"] = "warning"
                
            except Exception as e:
                logger.error(f"Metrics retrieval error: {e}")
        
        return metrics
    
    def monitor_events(self, duration: int = 60):
        """
        Monitor events for a specified duration
        
        Args:
            duration: Monitoring duration in seconds
        """
        
        print(f"Monitoring events for {duration} seconds...")
        
        start_time = datetime.now()
        event_count = 0
        
        while (datetime.now() - start_time).seconds < duration:
            # In production, this would consume from Kafka
            # For now, we simulate monitoring
            
            # Check if any events in mock handler
            if hasattr(self.kafka_handler, 'mock_events'):
                new_events = len(self.kafka_handler.mock_events) - event_count
                if new_events > 0:
                    print(f"  Detected {new_events} new events")
                    event_count = len(self.kafka_handler.mock_events)
            
            # Sleep briefly
            import time
            time.sleep(1)
        
        print(f"Monitoring complete. Total events: {event_count}")
    
    def _store_audit_log(self, log_entry: Dict):
        """Store audit log in database"""
        
        if self.db_session:
            try:
                audit_log = AuditLog(
                    event_type=log_entry["event_type"],
                    event_id=log_entry["event_id"],
                    agent_name=log_entry["agent_name"],
                    customer_id=log_entry["customer_id"],
                    action=log_entry["action"],
                    details=log_entry["details"],
                    status=log_entry["status"],
                    occurred_at=log_entry["occurred_at"]
                )
                
                self.db_session.add(audit_log)
                self.db_session.commit()
                
            except Exception as e:
                logger.error(f"Database storage error: {e}")
                if self.db_session:
                    self.db_session.rollback()
                # Fall back to memory storage
                if hasattr(self, 'memory_logs'):
                    self.memory_logs.append(log_entry)
        else:
            # Store in memory
            if hasattr(self, 'memory_logs'):
                self.memory_logs.append(log_entry)
    
    def _get_audit_logs(self, customer_id: Optional[str], 
                       start_date: datetime, 
                       end_date: datetime) -> List[Dict]:
        """Retrieve audit logs from database"""
        
        logs = []
        
        if self.db_session:
            try:
                query = self.db_session.query(AuditLog)
                
                # Apply filters
                if customer_id:
                    query = query.filter(AuditLog.customer_id == customer_id)
                
                query = query.filter(
                    AuditLog.occurred_at >= start_date,
                    AuditLog.occurred_at <= end_date
                )
                
                # Get results
                db_logs = query.order_by(AuditLog.occurred_at.desc()).all()
                
                for log in db_logs:
                    logs.append({
                        "event_type": log.event_type,
                        "agent_name": log.agent_name,
                        "customer_id": log.customer_id,
                        "status": log.status,
                        "occurred_at": log.occurred_at
                    })
                    
            except Exception as e:
                logger.error(f"Database query error: {e}")
        
        # Fall back to memory logs
        if not logs and hasattr(self, 'memory_logs'):
            for log in self.memory_logs:
                log_time = log.get("occurred_at")
                if isinstance(log_time, str):
                    log_time = datetime.fromisoformat(log_time)
                
                if start_date <= log_time <= end_date:
                    if not customer_id or log.get("customer_id") == customer_id:
                        logs.append(log)
        
        return logs
    
    def _analyze_logs(self, logs: List[Dict]) -> Dict:
        """Analyze audit logs for patterns"""
        
        analysis = {
            "event_counts": {},
            "agent_counts": {},
            "status_counts": {"success": 0, "failure": 0, "warning": 0},
            "timeline": []
        }
        
        for log in logs:
            # Count events
            event_type = log.get("event_type", "unknown")
            analysis["event_counts"][event_type] = analysis["event_counts"].get(event_type, 0) + 1
            
            # Count by agent
            agent = log.get("agent_name", "unknown")
            analysis["agent_counts"][agent] = analysis["agent_counts"].get(agent, 0) + 1
            
            # Count by status
            status = log.get("status", "unknown")
            if status in analysis["status_counts"]:
                analysis["status_counts"][status] += 1
        
        return analysis
    
    def _generate_report_text(self, analysis: Dict, customer_id: Optional[str],
                            start_date: datetime, end_date: datetime) -> str:
        """Generate audit report text"""
        
        if self.llm:
            # Use AI to generate report
            prompt = f"""
            Generate a professional audit report summary:
            
            Period: {start_date.date()} to {end_date.date()}
            Customer: {customer_id if customer_id else 'All customers'}
            
            Event Statistics:
            - Total events: {sum(analysis['event_counts'].values())}
            - Event types: {', '.join(analysis['event_counts'].keys())}
            - Success rate: {analysis['status_counts']['success'] / max(sum(analysis['status_counts'].values()), 1) * 100:.1f}%
            
            Agent Activity:
            {json.dumps(analysis['agent_counts'], indent=2)}
            
            Generate a 3-4 sentence executive summary of the audit findings.
            """
            
            try:
                return self.llm.run(prompt)
            except:
                pass
        
        # Fallback text generation
        total_events = sum(analysis['event_counts'].values())
        success_rate = 0
        if total_events > 0:
            success_rate = analysis['status_counts']['success'] / total_events * 100
        
        report = f"Audit Report for period {start_date.date()} to {end_date.date()}. "
        report += f"Total of {total_events} events processed"
        
        if customer_id:
            report += f" for customer {customer_id}"
        
        report += f" with {success_rate:.1f}% success rate. "
        
        # Most active agent
        if analysis['agent_counts']:
            most_active = max(analysis['agent_counts'], key=analysis['agent_counts'].get)
            report += f"Most active component: {most_active}. "
        
        # Issues
        failures = analysis['status_counts'].get('failure', 0)
        if failures > 0:
            report += f"Note: {failures} failed operations require attention."
        else:
            report += "All operations completed successfully."
        
        return report
    
    def _update_metrics(self, event_type: str):
        """Update real-time metrics in Redis"""
        
        if self.redis_client:
            try:
                # Increment counter
                counter_key = f"audit:counter:{event_type}"
                self.redis_client.incr(counter_key)
                
                # Update daily counter
                today_key = f"audit:daily:{datetime.now().strftime('%Y%m%d')}:{event_type}"
                self.redis_client.incr(today_key)
                self.redis_client.expire(today_key, 86400 * 7)  # Keep for 7 days
                
            except Exception as e:
                logger.error(f"Metrics update error: {e}")
    
    def _detect_anomalies(self, event_type: str, event_data: Dict) -> List[str]:
        """Detect anomalies in events"""
        
        anomalies = []
        
        # Check for repeated failures
        if event_data.get("status") == "failure":
            if self.redis_client:
                try:
                    failure_key = f"audit:failures:{event_data.get('customer_id', 'unknown')}"
                    failures = self.redis_client.incr(failure_key)
                    self.redis_client.expire(failure_key, 3600)  # Reset after 1 hour
                    
                    if failures > 5:
                        anomalies.append(f"Multiple failures detected for customer {event_data.get('customer_id')}")
                except:
                    pass
        
        # Check for unusual activity patterns
        if self.redis_client:
            try:
                # Check event rate
                rate_key = f"audit:rate:{event_type}"
                rate = self.redis_client.incr(rate_key)
                self.redis_client.expire(rate_key, 60)  # 1 minute window
                
                if rate > 100:
                    anomalies.append(f"High event rate detected for {event_type}")
            except:
                pass
        
        return anomalies
    
    def _handle_anomalies(self, anomalies: List[str]):
        """Handle detected anomalies"""
        
        for anomaly in anomalies:
            logger.warning(f"Anomaly detected: {anomaly}")
            
            # Log anomaly as special event
            self.kafka_handler.send_event(
                topic="audit-anomaly",
                key="anomaly",
                value={
                    "anomaly": anomaly,
                    "detected_at": datetime.now().isoformat()
                }
            )
            
            # Store in Redis for alerting
            if self.redis_client:
                try:
                    alert_key = f"audit:alert:{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    self.redis_client.setex(alert_key, 3600, anomaly)
                except:
                    pass


def test_audit_agent():
    """Test the Audit Logging Agent"""
    
    print("\n" + "="*60)
    print("TESTING AUDIT LOGGING AGENT")
    print("="*60)
    
    # Create agent
    agent = SAMAAuditLoggingAgent()
    
    # Test 1: Log various events
    print("\nTest 1: Logging events...")
    
    events = [
        {
            "type": "document-processed",
            "data": {
                "event_id": "doc_001",
                "agent_name": "DocumentIngestionAgent",
                "customer_id": "CUSTOMER_001",
                "action": "process_document",
                "status": "success"
            }
        },
        {
            "type": "kyc-validation-completed",
            "data": {
                "event_id": "kyc_001",
                "agent_name": "KYCValidationAgent",
                "customer_id": "CUSTOMER_001",
                "action": "validate_kyc",
                "status": "success"
            }
        },
        {
            "type": "compliance-summary-generated",
            "data": {
                "event_id": "sum_001",
                "agent_name": "ComplianceSummaryAgent",
                "customer_id": "CUSTOMER_001",
                "action": "generate_summary",
                "status": "failure"
            }
        }
    ]
    
    for event in events:
        result = agent.log_event(event["type"], event["data"])
        print(f"  Logged: {event['type']} - {result['logged']}")
    
    # Test 2: Generate audit report
    print("\nTest 2: Generating audit report...")
    
    report = agent.get_audit_report(customer_id="CUSTOMER_001")
    
    print(f"\nAudit Report:")
    print(f"  Report ID: {report['report_id']}")
    print(f"  Total Events: {report['total_events']}")
    print(f"  Period: {report['period']['start'][:10]} to {report['period']['end'][:10]}")
    
    if report.get('event_breakdown'):
        print(f"\nEvent Breakdown:")
        for event_type, count in report['event_breakdown'].items():
            print(f"    {event_type}: {count}")
    
    if report.get('agent_activity'):
        print(f"\nAgent Activity:")
        for agent, count in report['agent_activity'].items():
            print(f"    {agent}: {count}")
    
    print(f"\nReport Summary:")
    print(f"  {report.get('report_text', 'No summary generated')}")
    
    # Test 3: Get compliance metrics
    print("\nTest 3: Getting compliance metrics...")
    
    metrics = agent.get_compliance_metrics()
    
    print(f"\nCompliance Metrics:")
    print(f"  Events Today: {metrics['total_events_today']}")
    print(f"  Success Rate: {metrics['success_rate']:.1%}")
    print(f"  System Health: {metrics['system_health']}")
    print(f"  Recent Failures: {metrics['recent_failures']}")
    
    print("\n✅ Audit Logging Agent test complete!")


if __name__ == "__main__":
    test_audit_agent()