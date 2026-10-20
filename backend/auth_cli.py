"""Local-only development issuer. Tokens are secrets: redirect output to a private file."""
import argparse

from auth import AuthSettings, issue_viewer_token


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Issue a local viewer JWT valid for 15 minutes")
    parser.add_argument("--subject", default="local-operator")
    args = parser.parse_args()
    print(issue_viewer_token(AuthSettings.from_environment(), args.subject))
