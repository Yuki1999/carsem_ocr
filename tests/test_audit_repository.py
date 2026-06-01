from app.repositories.audit import redact_audit_payload


def test_redact_audit_payload_masks_secret_fields():
    payload = {
        "llm_api_key": "sk-secret",
        "nested": {"password": "pw", "safe": "value"},
    }

    redacted = redact_audit_payload(payload)

    assert redacted["llm_api_key"] == "***REDACTED***"
    assert redacted["nested"]["password"] == "***REDACTED***"
    assert redacted["nested"]["safe"] == "value"
