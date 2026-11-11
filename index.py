import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def handler(event, _context):
    if isinstance(event, str):
        return event.upper()

    # The manual test payload omits action; GitHub issues events include it.
    if not isinstance(event, dict) or event.get("action", "opened") != "opened":
        return "ignored"

    issue = event.get("issue")
    if not isinstance(issue, dict):
        return "ignored"

    issue_url = issue.get("html_url")
    owner = re.escape(os.environ["GITHUB_OWNER"])
    issue_pattern = rf"https://github\.com/{owner}/esep-webhooks/issues/[1-9][0-9]*"
    if not isinstance(issue_url, str) or not re.fullmatch(issue_pattern, issue_url, re.IGNORECASE):
        return "ignored"

    slack_url = os.environ.get("SLACK_URL")
    if not slack_url:
        raise RuntimeError("SLACK_URL is missing from the Lambda environment")

    payload = json.dumps({"text": f"Issue Created: {issue_url}"}).encode("utf-8")
    request = Request(
        slack_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            result = response.read(64).strip()
    except HTTPError as error:
        status = error.code
        error.close()
        raise RuntimeError(f"Slack returned HTTP {status}") from None
    except (URLError, TimeoutError):
        raise RuntimeError("Could not reach Slack") from None

    if result != b"ok":
        raise RuntimeError("Slack returned an unexpected response")
    return "ok"
