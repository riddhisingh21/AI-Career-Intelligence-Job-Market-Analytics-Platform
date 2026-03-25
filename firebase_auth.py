import json
import os
from urllib import error, request


FIREBASE_AUTH_BASE_URL = "https://identitytoolkit.googleapis.com/v1"
FIREBASE_TOKEN_REFRESH_URL = "https://securetoken.googleapis.com/v1/token"
FIREBASE_ERROR_MESSAGES = {
    "EMAIL_EXISTS": "An account with this email already exists.",
    "EMAIL_NOT_FOUND": "Invalid email or password.",
    "INVALID_PASSWORD": "Invalid email or password.",
    "INVALID_LOGIN_CREDENTIALS": "Invalid email or password.",
    "CONFIGURATION_NOT_FOUND": "Firebase Email/Password authentication is not enabled for this project.",
    "OPERATION_NOT_ALLOWED": "Firebase Email/Password authentication is not enabled for this project.",
    "PROJECT_NOT_FOUND": "The Firebase project configuration could not be found for this API key.",
    "API_KEY_INVALID": "The configured Firebase API key is invalid.",
    "MISSING_PASSWORD": "Password is required.",
    "MISSING_EMAIL": "Email is required.",
    "INVALID_EMAIL": "Please enter a valid email address.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please try again later.",
    "USER_DISABLED": "This account has been disabled.",
}


class FirebaseAuthError(Exception):
    pass


def resolve_firebase_api_key(secrets=None):
    secrets = secrets or {}
    firebase_secrets = secrets.get("firebase") or {}
    return (
        os.getenv("FIREBASE_API_KEY")
        or secrets.get("FIREBASE_API_KEY")
        or firebase_secrets.get("api_key")
    )


def resolve_firebase_project_id(secrets=None):
    secrets = secrets or {}
    firebase_secrets = secrets.get("firebase") or {}
    return (
        os.getenv("FIREBASE_PROJECT_ID")
        or secrets.get("FIREBASE_PROJECT_ID")
        or firebase_secrets.get("project_id")
    )


def _build_endpoint(action, api_key):
    return f"{FIREBASE_AUTH_BASE_URL}/accounts:{action}?key={api_key}"


def _format_firebase_error(message):
    raw_message = str(message or "").strip()
    error_code, separator, detail = raw_message.partition(" : ")
    normalized_code = error_code.strip()

    if normalized_code == "WEAK_PASSWORD" and detail.strip():
        detail_message = detail.strip()
        return detail_message[:1].upper() + detail_message[1:]

    if normalized_code in FIREBASE_ERROR_MESSAGES:
        return FIREBASE_ERROR_MESSAGES[normalized_code]

    if raw_message:
        return raw_message.replace("_", " ").capitalize()

    return "Firebase Authentication request failed."


def _extract_http_error_message(http_error):
    try:
        payload = json.loads(http_error.read().decode("utf-8"))
    except Exception:
        payload = {}

    message = payload.get("error", {}).get("message") or str(http_error)
    return _format_firebase_error(message)


def _post_json(url, payload):
    request_body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url,
        data=request_body,
        headers={"Content-Type": "application/json"},
    )

    with request.urlopen(http_request, timeout=20) as response:
        response_body = response.read().decode("utf-8")

    return json.loads(response_body) if response_body else {}


def _firebase_request(action, payload, api_key=None, secrets=None, http_post=None):
    resolved_api_key = api_key or resolve_firebase_api_key(secrets)

    if not resolved_api_key:
        raise FirebaseAuthError("FIREBASE_API_KEY is not configured.")

    post_json = http_post or _post_json
    endpoint = _build_endpoint(action, resolved_api_key)

    try:
        response_payload = post_json(endpoint, payload)
    except error.HTTPError as http_error:
        raise FirebaseAuthError(_extract_http_error_message(http_error)) from http_error
    except error.URLError as url_error:
        raise FirebaseAuthError("Could not reach Firebase Authentication.") from url_error
    except FirebaseAuthError:
        raise
    except Exception as request_error:
        raise FirebaseAuthError(f"Firebase Authentication request failed: {request_error}") from request_error

    if not isinstance(response_payload, dict):
        raise FirebaseAuthError("Firebase Authentication returned an invalid response.")

    return response_payload


def _normalize_auth_payload(payload):
    email = str(payload.get("email", "")).strip().lower()
    local_id = str(payload.get("localId", "")).strip()
    id_token = str(payload.get("idToken", "")).strip()
    refresh_token = str(payload.get("refreshToken", "")).strip()

    if not email or not local_id or not id_token:
        raise FirebaseAuthError("Firebase Authentication returned an incomplete response.")

    try:
        expires_in = int(str(payload.get("expiresIn", "")).strip())
    except (TypeError, ValueError):
        expires_in = None

    return {
        "email": email,
        "local_id": local_id,
        "id_token": id_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
    }


def sign_in_with_email_password(email, password, api_key=None, secrets=None, http_post=None):
    response_payload = _firebase_request(
        "signInWithPassword",
        {
            "email": str(email or "").strip().lower(),
            "password": str(password or ""),
            "returnSecureToken": True,
        },
        api_key=api_key,
        secrets=secrets,
        http_post=http_post,
    )
    return _normalize_auth_payload(response_payload)


def sign_up_with_email_password(email, password, api_key=None, secrets=None, http_post=None):
    response_payload = _firebase_request(
        "signUp",
        {
            "email": str(email or "").strip().lower(),
            "password": str(password or ""),
            "returnSecureToken": True,
        },
        api_key=api_key,
        secrets=secrets,
        http_post=http_post,
    )
    return _normalize_auth_payload(response_payload)


def send_password_reset_email(email, api_key=None, secrets=None, http_post=None):
    normalized_email = str(email or "").strip().lower()

    if not normalized_email:
        raise FirebaseAuthError("Email is required.")

    _firebase_request(
        "sendOobCode",
        {"requestType": "PASSWORD_RESET", "email": normalized_email},
        api_key=api_key,
        secrets=secrets,
        http_post=http_post,
    )


def refresh_id_token(refresh_token, api_key=None, secrets=None):
    """Exchange a Firebase refresh token for a fresh ID token.

    Returns a dict with ``id_token``, ``refresh_token``, and ``expires_in``.
    Raises :class:`FirebaseAuthError` on any failure.
    """
    resolved_api_key = api_key or resolve_firebase_api_key(secrets)
    if not resolved_api_key:
        raise FirebaseAuthError("FIREBASE_API_KEY is not configured.")

    url = f"{FIREBASE_TOKEN_REFRESH_URL}?key={resolved_api_key}"
    body = f"grant_type=refresh_token&refresh_token={refresh_token}".encode("utf-8")
    http_request = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with request.urlopen(http_request, timeout=20) as response:
            response_body = response.read().decode("utf-8")
        payload = json.loads(response_body) if response_body else {}
    except error.HTTPError as http_error:
        raise FirebaseAuthError(_extract_http_error_message(http_error)) from http_error
    except error.URLError as url_error:
        raise FirebaseAuthError("Could not reach Firebase Authentication.") from url_error

    id_token = str(payload.get("id_token") or payload.get("access_token") or "").strip()
    new_refresh_token = str(payload.get("refresh_token") or refresh_token).strip()

    try:
        expires_in = int(str(payload.get("expires_in", "")).strip())
    except (TypeError, ValueError):
        expires_in = None

    if not id_token:
        raise FirebaseAuthError("Firebase token refresh returned an incomplete response.")

    return {
        "id_token": id_token,
        "refresh_token": new_refresh_token,
        "expires_in": expires_in,
    }