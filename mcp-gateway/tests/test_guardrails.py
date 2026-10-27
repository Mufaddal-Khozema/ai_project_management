import pytest
from core.guardrails import GuardrailEngine, GuardrailViolation

def test_guardrail_read_role_cannot_write():
    auth = {"user_role": "read", "entitlements": {"has_subscription": True}}
    
    # Read tool should pass
    GuardrailEngine.verify_request("taiga_list_tasks", {}, auth)

    # Write tool should raise GuardrailViolation
    with pytest.raises(GuardrailViolation) as exc:
        GuardrailEngine.verify_request("taiga_create_task", {"subject": "Test"}, auth)
    assert exc.value.code == "GUARDRAIL_RBAC_WRITE_REQUIRED"

def test_guardrail_write_role_cannot_delete():
    auth = {"user_role": "write", "entitlements": {"has_subscription": True}}
    
    # Write tool should pass
    GuardrailEngine.verify_request("taiga_create_task", {"subject": "Test"}, auth)

    # Destructive tool should raise GuardrailViolation
    with pytest.raises(GuardrailViolation) as exc:
        GuardrailEngine.verify_request("taiga_delete_task", {"task_id": 123}, auth)
    assert exc.value.code == "GUARDRAIL_RBAC_ADMIN_REQUIRED"

def test_guardrail_admin_can_delete():
    auth = {"user_role": "admin", "entitlements": {"has_subscription": True}}
    # Admin should pass destructive check
    GuardrailEngine.verify_request("taiga_delete_task", {"task_id": 123}, auth)

def test_guardrail_sanitize_output():
    raw_payload = {
        "id": 101,
        "token": "secret_taiga_jwt_value",
        "nested": {
            "password_hash": "argon2_hash",
            "normal_field": "hello world"
        },
        "list_items": [
            {"auth_key": "12345", "name": "Item 1"}
        ]
    }
    cleaned = GuardrailEngine.sanitize_output(raw_payload)
    assert cleaned["token"] == "[REDACTED]"
    assert cleaned["nested"]["password_hash"] == "[REDACTED]"
    assert cleaned["nested"]["normal_field"] == "hello world"
    assert cleaned["list_items"][0]["auth_key"] == "[REDACTED]"
    assert cleaned["list_items"][0]["name"] == "Item 1"
