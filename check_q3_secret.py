#!/usr/bin/env python
"""
Quick script to check the Q3_INTEGRATION_SECRET on PythonAnywhere.
Upload this file to PythonAnywhere and run it in a Bash console:
    python check_q3_secret.py
"""
import os

print("=" * 60)
print("Checking Q3 Integration Secret Configuration")
print("=" * 60)

# Check all possible env vars
q3_secret = os.environ.get('Q3_INTEGRATION_SECRET', '(not set)')
aio_secret = os.environ.get('AIO_CLIENT_SECRET', '(not set)')
aio_token = os.environ.get('AIO_API_TOKEN', '(not set)')

print(f"\nQ3_INTEGRATION_SECRET: {q3_secret[:15]}... ({len(q3_secret)} chars)" if q3_secret != '(not set)' else f"\nQ3_INTEGRATION_SECRET: {q3_secret}")
print(f"AIO_CLIENT_SECRET: {aio_secret[:15]}... ({len(aio_secret)} chars)" if aio_secret != '(not set)' else f"AIO_CLIENT_SECRET: {aio_secret}")
print(f"AIO_API_TOKEN: {aio_token[:15]}... ({len(aio_token)} chars)" if aio_token != '(not set)' else f"AIO_API_TOKEN: {aio_token}")

# Which one will be used?
used_secret = q3_secret if q3_secret != '(not set)' else (aio_secret if aio_secret != '(not set)' else (aio_token if aio_token != '(not set)' else None))

print("\n" + "-" * 60)
if used_secret and used_secret != '(not set)':
    print(f"✓ SECRET THAT WILL BE USED:")
    print(f"  First 20 chars: {used_secret[:20]}")
    print(f"  Last 10 chars:  ...{used_secret[-10:]}")
    print(f"  Total length:   {len(used_secret)} characters")
    
    # Test if it matches expected
    expected = "5mpweqg0Hq19MBwbYLbwyjcRvfXa7tCg8FweWNFvuAk"
    if used_secret == expected:
        print("\n✓ SECRET MATCHES EXPECTED VALUE!")
    else:
        print("\n✗ SECRET DOES NOT MATCH EXPECTED VALUE!")
        print(f"  Expected: {expected}")
        print(f"  Got:      {used_secret}")
else:
    print("✗ NO Q3 SECRET CONFIGURED!")
    print("  Please set Q3_INTEGRATION_SECRET in your environment variables.")

print("\n" + "=" * 60)
