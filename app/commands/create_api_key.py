from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from app.config import get_settings
from app.db.models import ApiClient, ApiKey
from app.db.session import create_engine_from_settings, create_session_factory, session_scope, set_current_tenant
from app.repositories.tenants import get_or_create_tenant
from app.security.api_keys import generate_api_key, hash_api_key


@dataclass(frozen=True)
class CreatedApiKey:
    tenant_id: str
    tenant_slug: str
    client_id: str
    api_key_id: str
    api_key: str
    scopes: list[str]


def parse_scopes(raw: str) -> list[str]:
    normalized = str(raw or "").replace(",", " ")
    scopes: list[str] = []
    seen = set()
    for item in normalized.split():
        scope = item.strip()
        if not scope or scope in seen:
            continue
        seen.add(scope)
        scopes.append(scope)
    return scopes


def create_api_key(session, *, tenant_slug: str, name: str, scopes: list[str]) -> CreatedApiKey:
    settings = get_settings()
    tenant = get_or_create_tenant(session, tenant_slug, name=tenant_slug)
    set_current_tenant(session, str(tenant.id))
    client = ApiClient(
        tenant_id=tenant.id,
        name=name,
        status="active",
        scopes={"items": scopes},
    )
    api_key = generate_api_key(prefix=settings.api_key_prefix)
    row = ApiKey(
        tenant_id=tenant.id,
        client_id=client.id,
        name=name,
        key_hash=hash_api_key(api_key),
        scopes={"items": scopes},
        status="active",
    )
    session.add(client)
    session.flush()
    row.client_id = client.id
    session.add(row)
    session.flush()
    return CreatedApiKey(
        tenant_id=str(tenant.id),
        tenant_slug=tenant.slug,
        client_id=str(client.id),
        api_key_id=str(row.id),
        api_key=api_key,
        scopes=scopes,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a scoped TeleIDP API key for agent/skill access.")
    parser.add_argument("--tenant", default="default", help="Tenant slug.")
    parser.add_argument("--name", default="agent-client", help="API client/key display name.")
    parser.add_argument(
        "--scopes",
        default="documents:extract templates:read history:read",
        help="Comma or space separated scopes.",
    )
    args = parser.parse_args()

    engine = create_engine_from_settings(get_settings())
    factory = create_session_factory(engine)
    with session_scope(factory) as session:
        created = create_api_key(
            session,
            tenant_slug=args.tenant,
            name=args.name,
            scopes=parse_scopes(args.scopes),
        )
    print(json.dumps(created.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
