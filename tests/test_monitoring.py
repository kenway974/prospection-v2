"""C100 : erreurs remontées automatiquement, sans données personnelles ni secrets."""

from unittest import mock

from prospection.monitoring import scrub, start_monitoring


def test_C100_nothing_personal_or_secret_leaves() -> None:
    event = {
        "request": {"headers": {"Cookie": "session=…"}, "data": "mot de passe"},
        "user": {"ip_address": "1.2.3.4"}, "breadcrumbs": {"values": [{"message": "x"}]},
        "extra": {"clé": "AIza"},
        "exception": {"values": [{
            "value": "(psycopg.IntegrityError) doublon [SQL: INSERT …] [parameters: {'name': 'X'}]",
            "stacktrace": {"frames": [{"function": "f", "vars": {"key": "AIza-secret"}}]},
        }]},
        "logentry": {"message": "Erreur %s", "params": ["Boulangerie Martin"]},
    }  # fmt: skip
    clean = scrub(event, {})
    assert not {"request", "user", "breadcrumbs", "extra"} & clean.keys()
    [exception] = clean["exception"]["values"]
    assert exception["value"] == "(psycopg.IntegrityError) doublon"
    assert "vars" not in exception["stacktrace"]["frames"][0]
    assert "params" not in clean["logentry"]


def test_C100_only_when_configured() -> None:
    with mock.patch("sentry_sdk.init") as init:
        assert not start_monitoring(None, "app")
        init.assert_not_called()
        assert start_monitoring("https://cle@o1.ingest.sentry.io/1", "worker")
    options = init.call_args.kwargs
    assert options["send_default_pii"] is False and options["include_local_variables"] is False


def test_C100_postgres_detail_with_row_values_is_cut() -> None:
    raw = ('(psycopg.errors.NotNullViolation) null value in column "status"\n'
           "DETAIL:  Failing row contains (12, Boulangerie Martin, 0612345678).")  # fmt: skip
    clean = scrub({"exception": {"values": [{"value": raw}]}}, {})
    value = clean["exception"]["values"][0]["value"]
    assert value == '(psycopg.errors.NotNullViolation) null value in column "status"'
    unique = "duplicate key value violates unique constraint Key (kind, name_norm)=(x, martin)"
    assert (
        "martin"
        not in scrub({"exception": {"values": [{"value": unique}]}}, {})["exception"]["values"][0][
            "value"
        ]
    )
