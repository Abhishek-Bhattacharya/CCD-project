import json
import pytest
from phoenix_agent.audit_logger import AuditLogger


def test_audit_logging_and_masking(tmp_path):
    logger = AuditLogger(log_dir=str(tmp_path))
    event = logger.log_event(
        event_type="groq_inference",
        incident_id="inc-12345",
        commit_sha="sha998877",
        status="success",
        details={
            "api_key": "gsk_1234567890abcdef1234567890",
            "token": "ghp_1234567890abcdef1234567890",
            "message": "Groq returned patch with gsk_secret_token_1234567890",
            "tokens": 450
        }
    )

    events = logger.read_all_events()
    assert len(events) == 1
    logged = events[0]
    assert logged["event_type"] == "groq_inference"
    assert logged["status"] == "success"

    # Verify secrets were redacted in the saved log
    details = logged["details"]
    assert details["api_key"] == "[REDACTED]"
    assert details["token"] == "[REDACTED]"
    assert "gsk_1234567890abcdef1234567890" not in json.dumps(details)
