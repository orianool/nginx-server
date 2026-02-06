# `server_test.py`

This folder contains the **tester image** and the Python script that validates the running Nginx container.

## What the script tests

`server_test.py` performs two types of checks for each configured endpoint:

1) **Response validation** (`response_test`)
- Sends a single request to the endpoint.
- Verifies:
  - HTTP status code matches the expected status
  - Required response headers exist and match (substring match)
  - Required body markers exist (substring match)

2) **Rate-limit validation** (`limit_test`)
- Sends a burst of requests in parallel to the endpoint.
- Pass condition: at least **one** response is rate-limited (status is `429`).

### Current assertions (simple but extensible)

Currently, each endpoint test checks:
- 1 required header (example: `Content-Type` contains `text/html`)
- 1 meta tag marker (a required substring in the body)
- 1 additional required body string (often a unique `<h1>...</h1>`)
- verifies rate limit is operational

This is enough for simple validation. For more complex pages/APIs, add more required headers or body markers by extending the corresponding `Test` object in the `tests` list.

## How endpoints and expectations are set

In `main()` there are two lists that must stay aligned by index:

- `targets`: which endpoints to call
  - Each target includes:
    - `dest` (hostname)
    - `port` (e.g. `8080`)
    - `protocol` (`http` or `https`)
    - `method` (usually `GET`)

- `tests`: what to expect from each endpoint
  - Each entry is a `Test(status, headers, body_markers)`:
    - `status`: expected status code (example: `200`, `501`)
    - `headers`: dict of required headers (example: `{"Content-Type": "text/html"}`)
      - Matching is done by substring (so `text/html` matches `text/html; charset=utf-8`)
    - `body`: list of strings that must appear in the response body (meta tag, `<h1>`, etc.)

The script iterates with:

- `for target, test in zip(targets, tests): ...`

## HTTPS behavior (self-signed)

For `protocol == "https"`, requests are made using `http.client.HTTPSConnection` with an **unverified SSL context** (`ssl._create_unverified_context()`), so self-signed certificates work without installing a CA.

## Rate-limit check parameters

In `limit_test()`:
- `total = 40` requests are sent
- `workers = 10` threads are used

Adjusting these values changes how aggressively the limiter is exercised.

## Environment variables

- `NGINX_HOST` (default: `localhost`)
  - In `docker compose`, this is usually set to the service name (example: `nginx`).

## Exit codes

- `0` success
- `10` connectivity failure (connection refused / DNS / timeout)
- `20` wrong status code (or rate-limit not triggered)
- `30` header check failed
- `40` body/content check failed
- `50` unexpected script error

## How to run

Local (Nginx must already be running and ports exposed):

```bash
python3 server_test.py
```

With a custom host (example for docker-compose network):

```bash
NGINX_HOST=nginx python3 server_test.py
```
