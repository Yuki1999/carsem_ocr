from app.commands.create_api_key import parse_scopes


def test_parse_scopes_accepts_comma_and_space_separated_values():
    scopes = parse_scopes("documents:extract, templates:read history:read")

    assert scopes == ["documents:extract", "templates:read", "history:read"]
