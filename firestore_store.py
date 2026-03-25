"""Firebase Firestore integration for persisting per-user analysis history."""
import json
from datetime import datetime, UTC
from urllib import error, request


FIRESTORE_BASE_URL = "https://firestore.googleapis.com/v1"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _firestore_request(method, path, id_token, payload=None):
    url = f"{FIRESTORE_BASE_URL}/{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json",
    }
    http_request = request.Request(url, data=body, headers=headers, method=method)
    with request.urlopen(http_request, timeout=20) as response:
        response_body = response.read().decode("utf-8")
    return json.loads(response_body) if response_body else {}


def _to_firestore_value(value):
    """Convert a Python value to a Firestore REST API typed value object."""
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, list):
        return {"arrayValue": {"values": [_to_firestore_value(v) for v in value]}}
    if value is None:
        return {"nullValue": None}
    return {"stringValue": str(value)}


def _from_firestore_value(value_dict):
    """Convert a Firestore REST API typed value object to a plain Python value."""
    if not isinstance(value_dict, dict):
        return None
    if "stringValue" in value_dict:
        return value_dict["stringValue"]
    if "doubleValue" in value_dict:
        return float(value_dict["doubleValue"])
    if "integerValue" in value_dict:
        return int(value_dict["integerValue"])
    if "booleanValue" in value_dict:
        return value_dict["booleanValue"]
    if "arrayValue" in value_dict:
        return [_from_firestore_value(v) for v in value_dict["arrayValue"].get("values", [])]
    if "nullValue" in value_dict:
        return None
    return None


def _collection_path(project_id, user_id):
    return f"projects/{project_id}/databases/(default)/documents/users/{user_id}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_analysis_firestore(user_id, id_token, project_id, resume_name, score,
                            interpretation, matched_skills, missing_skills):
    """Save one analysis record to the user's Firestore subcollection."""
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    doc = {
        "fields": {
            "created_at": _to_firestore_value(created_at),
            "resume_name": _to_firestore_value(resume_name),
            "score": _to_firestore_value(float(score)),
            "interpretation": _to_firestore_value(interpretation),
            "matched_skills": _to_firestore_value(list(matched_skills or [])),
            "missing_skills": _to_firestore_value(list(missing_skills or [])),
        }
    }
    path = f"{_collection_path(project_id, user_id)}/analyses"
    _firestore_request("POST", path, id_token, doc)


def get_recent_analyses_firestore(user_id, id_token, project_id, limit=5):
    """Return up to *limit* analyses ordered newest-first from Firestore."""
    parent_path = _collection_path(project_id, user_id)
    query_path = f"{parent_path}:runQuery"
    query = {
        "structuredQuery": {
            "from": [{"collectionId": "analyses"}],
            "orderBy": [{"field": {"fieldPath": "created_at"}, "direction": "DESCENDING"}],
            "limit": limit,
        }
    }
    results = _firestore_request("POST", query_path, id_token, query)

    analyses = []
    for item in results:
        doc = item.get("document")
        if not doc:
            continue
        fields = doc.get("fields", {})
        analyses.append({
            "created_at": _from_firestore_value(fields.get("created_at", {"stringValue": ""})),
            "resume_name": _from_firestore_value(fields.get("resume_name", {"stringValue": ""})),
            "score": _from_firestore_value(fields.get("score", {"doubleValue": 0.0})),
            "interpretation": _from_firestore_value(fields.get("interpretation", {"stringValue": ""})),
            "matched_skills": _from_firestore_value(fields.get("matched_skills", {"arrayValue": {"values": []}})),
            "missing_skills": _from_firestore_value(fields.get("missing_skills", {"arrayValue": {"values": []}})),
            "_doc_name": doc.get("name", ""),
        })
    return analyses


def clear_analyses_firestore(user_id, id_token, project_id):
    """Delete all analysis documents for the user from Firestore."""
    list_path = f"{_collection_path(project_id, user_id)}/analyses?pageSize=500"
    result = _firestore_request("GET", list_path, id_token)
    documents = result.get("documents", [])
    if not documents:
        return
    writes = [{"delete": doc["name"]} for doc in documents]
    batch_path = f"projects/{project_id}/databases/(default)/documents:batchWrite"
    _firestore_request("POST", batch_path, id_token, {"writes": writes})

