"""
utils/audit_log.py
Enterprise audit logging system for compliance.
Tracks every agent action, data access, and sensitive transition.
Logs to both structured logs and optionally a database table.
"""
import datetime
import json
import logging
from typing import Any, Dict, Optional
from utils.logging_config import logger as struct_logger
from graph.state import CRMAgentState

class AuditLogger:
    @staticmethod
    def log_event(
        event_type: str,
        session_id: str,
        user_id: str,
        agent_name: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
        data_accessed: Optional[list] = None,
        status: str = "success"
    ):
        """
        Records a compliance-grade audit event.
        event_type: LOGIN | AGENT_START | DATA_ACCESS | EMAIL_DRAFTED | CRM_WRITE | HUMAN_ESCALATION
        """
        event = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "session_id": session_id,
            "user_id": user_id,
            "agent": agent_name,
            "details": action_details or {},
            "data_accessed": data_accessed or [],
            "status": status,
            "audit": True # Flag for log aggregation filters
        }
        
        # Log to structured system logs
        struct_logger.info("audit_event", **event)
        
        # In the future, this would also write to a dedicated PostgreSQL 'audit_logs' table
        # for immutable compliance records.
        return event

    @classmethod
    def log_agent_run(cls, state: CRMAgentState, agent_name: str, details: Dict[str, Any]):
        """Helper to log from inside a LangGraph node."""
        return cls.log_event(
            event_type="AGENT_EXECUTION",
            session_id=state.get("session_id", "unknown"),
            user_id="system", # Would come from state in real multi-tenant app
            agent_name=agent_name,
            action_details=details,
            data_accessed=state.get("data_sources", [])
        )

audit_log = AuditLogger()
