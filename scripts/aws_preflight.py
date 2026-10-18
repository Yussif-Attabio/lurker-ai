#!/usr/bin/env python3
"""Read-only AWS credential preflight. Never invokes Bedrock or creates resources."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound


def cli_version() -> str | None:
    """Return the installed AWS CLI version without reading credentials."""
    executable = shutil.which("aws")
    if executable is None:
        return None
    completed = subprocess.run(
        [executable, "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    return (completed.stdout or completed.stderr).strip() or None


def verify_identity(profile: str | None, region: str) -> dict[str, Any]:
    """Call only STS GetCallerIdentity through the application's SDK path.

    The returned identity is used only to establish success and is never printed.
    The CRT requirement lets boto3 consume AWS CLI login-session credentials.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    if session.get_credentials() is None:
        raise NoCredentialsError()
    return session.client("sts", region_name=region).get_caller_identity()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE"))
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-2"))
    args = parser.parse_args()

    version = cli_version()
    print(f"aws_cli={version or 'NOT_INSTALLED'}")
    print(f"region={args.region}")
    print(f"profile={args.profile or 'default credential chain'}")

    try:
        verify_identity(args.profile, args.region)
    except (BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound) as exc:
        print(f"sts_identity=FAILED ({type(exc).__name__})", file=sys.stderr)
        return 2

    print("sts_identity=OK")
    print("identity_fields=SUPPRESSED")
    print("bedrock_invoked=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
