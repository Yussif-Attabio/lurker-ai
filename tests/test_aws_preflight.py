"""Ensure the AWS preflight is read-only and suppresses identity output."""

from __future__ import annotations

from scripts import aws_preflight


def test_preflight_uses_sts_only(monkeypatch) -> None:
    requested_services: list[str] = []

    class Credentials:
        pass

    class StsClient:
        def get_caller_identity(self):
            return {"Account": "private", "Arn": "private", "UserId": "private"}

    class Session:
        def __init__(self, **kwargs):
            pass

        def get_credentials(self):
            return Credentials()

        def client(self, service_name: str, **kwargs):
            requested_services.append(service_name)
            return StsClient()

    monkeypatch.setattr(aws_preflight.boto3, "Session", Session)
    identity = aws_preflight.verify_identity(None, "us-east-2")

    assert identity["Account"] == "private"
    assert requested_services == ["sts"]
