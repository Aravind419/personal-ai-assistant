from app.core.security import encrypt_secret, decrypt_secret, mask_secret


def test_encryption_and_decryption_roundtrip():
    original = "sk-or-v1-super-secret-openrouter-key-12345"
    cipher = encrypt_secret(original)
    assert cipher is not None
    assert cipher != original

    decrypted = decrypt_secret(cipher)
    assert decrypted == original


def test_encryption_empty_handling():
    assert encrypt_secret(None) is None
    assert encrypt_secret("") is None
    assert decrypt_secret(None) is None
    assert decrypt_secret("") is None
    assert decrypt_secret("invalid-garbage-cipher") is None


def test_mask_secret():
    assert mask_secret("sk-or-v1-abcdef1234567890") == "sk-or••••••••7890"
    assert mask_secret("short") == "••••••••"
    assert mask_secret(None) is None
