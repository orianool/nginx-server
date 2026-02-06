# Nginx Server and Tester

This project builds an Ubuntu-based Nginx image that exposes three **endpoints** from a single container (implemented as multiple Nginx `server` blocks), including a **HTTPS** endpoint. Also includes a **rate limiting** feature, and a **Python tester** image to validate behavior.

## Requirements
- Docker Engine + Docker Compose (v2)
- On some systems you may need `sudo` for Docker commands.

## Run locally

### Run Nginx only
```bash
docker compose up -d --build nginx
```

Stop/cleanup:
```bash
docker compose down
```

### Run tests (Nginx + tester)
Build images and run tests with:
```bash
docker compose up --build --exit-code-from tester --abort-on-container-exit
```

Cleanup:
```bash
docker compose down -v --remove-orphans
```

## Nginx Configurations
### Endpoints
- `http://localhost:8080/`
  - Serves a custom HTML page from `/usr/share/nginx/html/index.html`
  - There is a small surprise, I recommend accessing the endpoint with Google Chrome if possible.
- `http://localhost:8081/`
  - Always returns an HTTP error (default `501`) and serves a custom error page body (`custom_501.html`).
  - `501 Not Implemented` seems to be the most fitting error since nothing is implemented on this endpoint.
- `https://localhost:8443/`
  - HTTPS with a self-signed certificate; serves the same content as `8080`.

### Rate limiting
- Configured using `limit_req_zone` + `limit_req`.
- Default: **5 requests/second** with `burst=5`.
- When the limit is hit, Nginx returns **429** (`limit_req_status 429;`).

## Images

This project builds two Docker images via `docker compose`:

- **`nginx` (nginx server)**  
  Ubuntu-based image with Nginx, `servers.conf`, and the HTML files under `html/`.  
  It serves:
  - `8080` — custom HTML page
  - `8081` — custom error response (default `501`)
  - `8443` — HTTPS (self-signed certificate)

- **`tester`**  
  Python image that runs `tests/server_test.py`. It sends requests to the `nginx` container (over the compose network) and exits:
  - `0` if all checks pass
  - non-zero if any check fails
  - see /tests/README.md for more details on what is tested and how.

## Repository layout
- `servers.conf` – Nginx server blocks and rate limit configuration
- `Dockerfile` – Ubuntu-based Nginx image build
- `html/index.html` – custom HTML page served on `8080` and `8443`
- `html/custom_501.html` – custom error body used by `8081`
- `docker-compose.yaml` – runs `nginx` + `tester`
- `tests/Dockerfile` – tester image build
- `tests/server_test.py` – Python test script executed by `tester`
- `.github/workflows/ci.yml` – GitHub Actions workflow

## Manual checks

### HTTP
```bash
curl -i http://localhost:8080/
curl -i http://localhost:8081/
```

### HTTPS (self-signed)
Use `-k` to skip certificate verification:
```bash
curl -k -i https://localhost:8443/
```

### Rate limit quick check
```bash
seq 1 40 | xargs -n1 -P10 curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/
```
You should see some `200` and, when limiting triggers, some `429`.

## CI (GitHub Actions)
The workflow:
- Builds the Docker images
- Runs `docker compose`
- Uploads an artifact containing a marker file:
  - `succeeded` if tests pass
  - `fail` if tests fail
(Optional) logs can also be uploaded as a separate file like `compose.log`.
```bash
sudo docker compose up --build --exit-code-from tester --abort-on-container-exit
