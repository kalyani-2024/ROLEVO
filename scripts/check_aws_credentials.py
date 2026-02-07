#!/usr/bin/env python3
"""Check AWS credentials by calling STS GetCallerIdentity.

Usage:
  python scripts/check_aws_credentials.py
  python scripts/check_aws_credentials.py --access-key ABC --secret-key XYZ

The script prefers explicit CLI args, then environment variables (`AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`). It prints the returned
identity JSON on success and exits non-zero on error.
"""
import argparse
import json
import os
import sys

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError


def parse_args():
    p = argparse.ArgumentParser(description="Validate AWS credentials via STS GetCallerIdentity")
    p.add_argument("--access-key", help="AWS access key id")
    p.add_argument("--secret-key", help="AWS secret access key")
    p.add_argument("--session-token", help="AWS session token (optional)")
    p.add_argument("--region", help="AWS region (optional)")
    return p.parse_args()


def main():
    args = parse_args()

    access_key = args.access_key or os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = args.secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
    session_token = args.session_token or os.environ.get("AWS_SESSION_TOKEN")
    region = args.region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")

    if not access_key or not secret_key:
        print("ERROR: AWS access key or secret key not provided (env or CLI).", file=sys.stderr)
        sys.exit(2)

    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region,
        )
        sts = session.client("sts")
        resp = sts.get_caller_identity()
        print("OK: credentials are valid. Returned identity:")
        print(json.dumps(resp, indent=2))
        return 0
    except NoCredentialsError:
        print("ERROR: No credentials available.", file=sys.stderr)
        return 2
    except EndpointConnectionError as e:
        print(f"ERROR: Endpoint connection error: {e}", file=sys.stderr)
        return 4
    except ClientError as e:
        # AWS returned an error (e.g., invalid credentials)
        print("ERROR: AWS ClientError:", file=sys.stderr)
        try:
            err = e.response.get("Error", {})
            print(json.dumps(err, indent=2), file=sys.stderr)
        except Exception:
            print(str(e), file=sys.stderr)
        return 3
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
