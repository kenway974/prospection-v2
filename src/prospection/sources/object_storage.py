"""Dépôt d'un fichier sur un stockage objet compatible S3 (Cloudflare R2, Scaleway…) pour
la sauvegarde quotidienne (C91). Signature AWS v4, bibliothèque standard seulement."""

import hashlib
import hmac
from datetime import datetime
from urllib.parse import quote, urlsplit

import httpx

UPLOAD_TIMEOUT = 120.0


class UploadFailed(Exception):
    """Le stockage refuse ou ne répond pas ; le message ne contient aucun secret."""


def _hmac(key: bytes, text: str) -> bytes:
    return hmac.new(key, text.encode(), hashlib.sha256).digest()


def signed_put_headers(
    url: str, body: bytes, access_key: str, secret_key: str, region: str, now: datetime
) -> dict[str, str]:
    """En-têtes d'un PUT signé (AWS Signature v4, service s3, adresse de style chemin)."""
    parts = urlsplit(url)
    amz_date, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    payload = hashlib.sha256(body).hexdigest()
    headers = {"host": parts.netloc, "x-amz-content-sha256": payload, "x-amz-date": amz_date}
    names = sorted(headers)
    signed = ";".join(names)
    canonical = "\n".join(
        ["PUT", quote(parts.path, safe="/-_.~"), parts.query,
         *(f"{n}:{headers[n]}" for n in names), "", signed, payload]
    )  # fmt: skip
    scope = f"{day}/{region}/s3/aws4_request"
    to_sign = "\n".join(
        ["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()]
    )
    key = _hmac(
        _hmac(_hmac(_hmac(f"AWS4{secret_key}".encode(), day), region), "s3"), "aws4_request"
    )
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    authorization = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders={signed}, "
        f"Signature={signature}"
    )
    return {"x-amz-content-sha256": payload, "x-amz-date": amz_date, "Authorization": authorization}


def put_object(
    client: httpx.Client, url: str, body: bytes, access_key: str, secret_key: str, region: str,
    now: datetime,
) -> None:  # fmt: skip
    headers = signed_put_headers(url, body, access_key, secret_key, region, now)
    try:
        response = client.put(url, content=body, headers=headers, timeout=UPLOAD_TIMEOUT)
    except httpx.HTTPError as error:
        raise UploadFailed(f"stockage injoignable ({type(error).__name__})") from None
    if response.status_code != 200:
        raise UploadFailed(f"stockage : réponse {response.status_code}")
