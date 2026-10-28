"""C91 : dépôt signé sur un stockage compatible S3 (aucun réseau : faux serveur)."""

from datetime import UTC, datetime

import httpx
import pytest

from prospection.sources.object_storage import UploadFailed, put_object, signed_put_headers
from tests.fake_http import fake_client, timeout

NOW = datetime(2026, 10, 28, 3, 15, tzinfo=UTC)
URL = "https://acct.r2.cloudflarestorage.com/sauvegardes/prospection-28.dump.chiffre"


def test_C91_signature_matches_aws_reference() -> None:
    """Valeur calculée par botocore (bibliothèque officielle d'AWS) pour la même requête."""
    headers = signed_put_headers(
        URL, b"donnees chiffrees", "AKIDTEST", "secretTEST/abc", "auto", NOW
    )
    assert headers["x-amz-date"] == "20261028T031500Z"
    assert headers["Authorization"] == (
        "AWS4-HMAC-SHA256 Credential=AKIDTEST/20261028/auto/s3/aws4_request, "
        "SignedHeaders=host;x-amz-content-sha256;x-amz-date, "
        "Signature=a598c8790a78f8993dfcdca881c12f5144d7bc71c9bb144f2c173f6f7d9f648b"
    )


def test_C91_upload_refused_or_unreachable_says_so_without_secret() -> None:
    client, seen = fake_client(lambda r: httpx.Response(200))
    put_object(client, URL, b"x", "AKIDTEST", "secretTEST", "auto", NOW)
    assert seen.requests[0].method == "PUT" and seen.requests[0].content == b"x"
    refused, _ = fake_client(
        lambda r: httpx.Response(403, text="<Error>SignatureDoesNotMatch</Error>")
    )
    with pytest.raises(UploadFailed, match="réponse 403") as error:
        put_object(refused, URL, b"x", "AKIDTEST", "secretTEST", "auto", NOW)
    assert "secretTEST" not in str(error.value)
    with pytest.raises(UploadFailed, match="injoignable"):
        put_object(fake_client(timeout)[0], URL, b"x", "AKIDTEST", "secretTEST", "auto", NOW)
