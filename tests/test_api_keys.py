from app.security.api_keys import generate_api_key, hash_api_key, verify_api_key


def test_api_key_hash_verifies_without_storing_plain_secret():
    key = generate_api_key(prefix="tidp")

    digest = hash_api_key(key)

    assert key.startswith("tidp_")
    assert key not in digest
    assert verify_api_key(key, digest)
    assert not verify_api_key(key + "x", digest)
