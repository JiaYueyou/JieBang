"""JWT + 密码哈希单元测试"""

import time
import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token


class TestPasswordHash:
    def test_hash_and_verify(self):
        h = hash_password("hello")
        assert h != "hello"
        assert verify_password("hello", h)

    def test_hash_is_random(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_verify_wrong(self):
        h = hash_password("correct")
        assert not verify_password("wrong", h)


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token({"user_id": 1, "username": "admin"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["username"] == "admin"

    def test_decode_invalid_token(self):
        assert decode_token("not.a.token") is None

    def test_decode_expired_token(self):
        # create a token that expired 1 hour ago
        from datetime import datetime, timedelta, timezone
        from jose import jwt
        from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM

        expired_payload = {
            "user_id": 1,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        assert decode_token(expired_token) is None
