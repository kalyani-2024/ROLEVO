#!/usr/bin/env python3
"""Synthesize speech using Amazon Polly and save to a file.

Usage examples:
  python scripts/polly_tts.py --text "Hello world" --voice Joanna --output hello.mp3
  python scripts/polly_tts.py --text-file message.txt --voice Matthew --format pcm --output message.pcm

Credentials are taken from CLI args, then environment variables, then AWS config.
"""
import argparse
import os
import sys

import boto3
from botocore.exceptions import ClientError


def parse_args():
    p = argparse.ArgumentParser(description="Polly TTS: synthesize text to audio file")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="Text to synthesize (enclose in quotes)")
    group.add_argument("--text-file", help="Path to a text file whose contents will be synthesized")

    p.add_argument("--voice", default="Joanna", help="Polly voice id (default: Joanna)")
    p.add_argument("--format", choices=["mp3", "pcm", "ogg_vorbis"], default="mp3", help="Output audio format (default: mp3)")
    p.add_argument("--output", default="output.mp3", help="Output filename (default: output.mp3)")
    p.add_argument("--engine", choices=["standard", "neural"], default="neural", help="Polly engine (default: neural)")
    p.add_argument("--access-key", help="AWS access key id (optional)")
    p.add_argument("--secret-key", help="AWS secret access key (optional)")
    p.add_argument("--session-token", help="AWS session token (optional)")
    p.add_argument("--region", help="AWS region (optional)")
    return p.parse_args()


def load_text(args):
    if args.text:
        return args.text
    with open(args.text_file, "r", encoding="utf-8") as fh:
        return fh.read()


def main():
    args = parse_args()

    text = load_text(args)
    output = args.output

    # Ensure output filename extension matches format if user didn't provide
    if args.format == "mp3" and not output.lower().endswith(".mp3"):
        output = output + ".mp3"
    if args.format == "pcm" and not (output.lower().endswith(".pcm") or output.lower().endswith(".wav")):
        output = output + ".pcm"
    if args.format == "ogg_vorbis" and not output.lower().endswith(".ogg"):
        output = output + ".ogg"

    # Prepare boto3 session. Prefer CLI args, then environment, then default to us-east-1.
    session_kwargs = {}
    if args.access_key and args.secret_key:
        session_kwargs.update(
            aws_access_key_id=args.access_key,
            aws_secret_access_key=args.secret_key,
            aws_session_token=args.session_token,
        )

    # Resolve region: CLI -> env AWS_REGION/AWS_DEFAULT_REGION -> fallback
    region = args.region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    session_kwargs["region_name"] = region

    try:
        session = boto3.Session(**session_kwargs)
        polly = session.client("polly")

        # Polly requires plain text or SSML; here we send plain text
        resp = polly.synthesize_speech(
            Text=text,
            OutputFormat=args.format,
            VoiceId=args.voice,
            Engine=args.engine,
        )

        # Stream the audio to file
        if "AudioStream" in resp:
            with open(output, "wb") as f:
                f.write(resp["AudioStream"].read())
            print(f"OK: audio written to {output}")
            return 0
        else:
            print("ERROR: No AudioStream in Polly response", file=sys.stderr)
            return 3

    except ClientError as e:
        print("ERROR: AWS ClientError:", e, file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: unexpected error: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
