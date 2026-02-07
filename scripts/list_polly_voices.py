#!/usr/bin/env python3
"""List Amazon Polly voices and show which voices match requested languages.

Usage:
  python scripts/list_polly_voices.py
  python scripts/list_polly_voices.py --region us-east-1

Reads AWS credentials from CLI args, environment, or AWS config.
"""
import argparse
import os
import sys
import json

import boto3
from botocore.exceptions import ClientError


REQUESTED = {
    'English': 'en',
    'Hindi': 'hi',
    'Tamil': 'ta',
    'Telugu': 'te',
    'Kannada': 'kn',
    'Marathi': 'mr',
    'Bengali': 'bn',
    'Malayalam': 'ml',
    'French': 'fr',
    'Arabic': 'ar',
    'Gujarati': 'gu',
}


def parse_args():
    p = argparse.ArgumentParser(description="List Amazon Polly voices and report by language")
    p.add_argument("--region", help="AWS region (optional)")
    p.add_argument("--access-key", help="AWS access key id (optional)")
    p.add_argument("--secret-key", help="AWS secret access key (optional)")
    p.add_argument("--session-token", help="AWS session token (optional)")
    p.add_argument("--json", action="store_true", help="Output full voice list as JSON")
    return p.parse_args()


def get_all_voices(polly):
    voices = []
    next_token = None
    while True:
        if next_token:
            resp = polly.describe_voices(NextToken=next_token)
        else:
            resp = polly.describe_voices()
        voices.extend(resp.get("Voices", []))
        next_token = resp.get("NextToken")
        if not next_token:
            break
    return voices


def main():
    args = parse_args()

    region = args.region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

    session_kwargs = {"region_name": region}
    if args.access_key and args.secret_key:
        session_kwargs.update(
            aws_access_key_id=args.access_key,
            aws_secret_access_key=args.secret_key,
            aws_session_token=args.session_token,
        )

    try:
        session = boto3.Session(**session_kwargs)
        polly = session.client("polly")

        voices = get_all_voices(polly)

        # Map voices by LanguageCode
        by_lang = {}
        for v in voices:
            lc = v.get("LanguageCode", "unknown")
            by_lang.setdefault(lc, []).append(v)

        print(f"Total voices available: {len(voices)}\n")

        results = {}
        # For each requested language, find voices whose LanguageCode starts with the two-letter code
        for name, code in REQUESTED.items():
            matches = []
            for lc, vs in by_lang.items():
                if lc.startswith(code):
                    for v in vs:
                        matches.append({
                            "Name": v.get("Name"),
                            "LanguageCode": v.get("LanguageCode"),
                            "Gender": v.get("Gender"),
                            "SupportedEngines": v.get("SupportedEngines", []),
                        })
            results[name] = matches

        # Print human-readable summary
        for name in REQUESTED.keys():
            matches = results.get(name, [])
            print(f"{name} ({REQUESTED[name]}): {len(matches)} voice(s)")
            if matches:
                for m in matches:
                    engines = ",".join(m.get("SupportedEngines", []))
                    print(f"  - {m['Name']} ({m['LanguageCode']}, {m['Gender']}) engines: {engines}")
            print()

        if args.json:
            print("\nFull JSON output:\n")
            print(json.dumps(results, indent=2))

        return 0

    except ClientError as e:
        print(f"ERROR: AWS ClientError: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: unexpected error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
