import io
import os
import unittest
from unittest import mock
from urllib.error import HTTPError

from firebase_auth import (
    FirebaseAuthError,
    resolve_firebase_api_key,
    send_password_reset_email,
    sign_in_with_email_password,
    sign_up_with_email_password,
)


class FirebaseConfigTests(unittest.TestCase):
    @mock.patch.dict(os.environ, {"FIREBASE_API_KEY": "env-key"}, clear=True)
    def test_resolve_firebase_api_key_prefers_environment_value(self):
        secrets = {"FIREBASE_API_KEY": "secret-key", "firebase": {"api_key": "nested-key"}}
        self.assertEqual(resolve_firebase_api_key(secrets), "env-key")

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_resolve_firebase_api_key_supports_nested_secrets(self):
        self.assertEqual(resolve_firebase_api_key({"firebase": {"api_key": "nested-key"}}), "nested-key")


class FirebaseAuthFlowTests(unittest.TestCase):
    def test_sign_in_with_email_password_normalizes_success_payload(self):
        captured = {}

        def fake_post(url, payload):
            captured["url"] = url
            captured["payload"] = payload
            return {
                "email": "USER@example.com",
                "localId": "local-123",
                "idToken": "id-token",
                "refreshToken": "refresh-token",
                "expiresIn": "3600",
            }

        result = sign_in_with_email_password(" USER@example.com ", "secret123", api_key="api-key", http_post=fake_post)

        self.assertTrue(captured["url"].endswith("accounts:signInWithPassword?key=api-key"))
        self.assertEqual(captured["payload"]["email"], "user@example.com")
        self.assertTrue(captured["payload"]["returnSecureToken"])
        self.assertEqual(result["email"], "user@example.com")
        self.assertEqual(result["local_id"], "local-123")
        self.assertEqual(result["expires_in"], 3600)

    def test_sign_up_with_email_password_surfaces_friendly_http_error(self):
        def fake_post(url, payload):
            raise HTTPError(
                url,
                400,
                "Bad Request",
                hdrs=None,
                fp=io.BytesIO(b'{"error": {"message": "EMAIL_EXISTS"}}'),
            )

        with self.assertRaisesRegex(FirebaseAuthError, "already exists"):
            sign_up_with_email_password("user@example.com", "secret123", api_key="api-key", http_post=fake_post)

    def test_sign_up_with_email_password_surfaces_configuration_error(self):
        def fake_post(url, payload):
            raise HTTPError(
                url,
                400,
                "Bad Request",
                hdrs=None,
                fp=io.BytesIO(b'{"error": {"message": "CONFIGURATION_NOT_FOUND"}}'),
            )

        with self.assertRaisesRegex(FirebaseAuthError, "Email/Password authentication is not enabled"):
            sign_up_with_email_password("user@example.com", "secret123", api_key="api-key", http_post=fake_post)

    def test_send_password_reset_email_posts_password_reset_request(self):
        captured = {}

        def fake_post(url, payload):
            captured["url"] = url
            captured["payload"] = payload
            return {"email": payload["email"]}

        send_password_reset_email(" person@example.com ", api_key="api-key", http_post=fake_post)

        self.assertTrue(captured["url"].endswith("accounts:sendOobCode?key=api-key"))
        self.assertEqual(captured["payload"], {"requestType": "PASSWORD_RESET", "email": "person@example.com"})

    def test_sign_in_requires_configured_api_key(self):
        with self.assertRaisesRegex(FirebaseAuthError, "FIREBASE_API_KEY"):
            sign_in_with_email_password("user@example.com", "secret123", api_key=None, secrets={})


if __name__ == "__main__":
    unittest.main()