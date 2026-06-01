import pytest

from app.security.tenant_context import ScopeError, TenantContext, require_scopes


def test_require_scopes_allows_present_scope():
    context = TenantContext(
        tenant_id="00000000-0000-0000-0000-000000000001",
        actor_type="agent",
        actor_id="api-key-1",
        scopes=frozenset({"documents:extract"}),
        request_id="req-1",
    )

    require_scopes(context, {"documents:extract"})


def test_require_scopes_rejects_missing_scope():
    context = TenantContext(
        tenant_id="00000000-0000-0000-0000-000000000001",
        actor_type="agent",
        actor_id="api-key-1",
        scopes=frozenset({"templates:read"}),
        request_id="req-1",
    )

    with pytest.raises(ScopeError):
        require_scopes(context, {"documents:extract"})
