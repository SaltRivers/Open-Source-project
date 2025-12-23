# Halligan

[![Paper](https://img.shields.io/badge/Paper-green)](http://linyun.info/publications/usenix-sec25.pdf)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Halligan is a vision-language model (VLM) agent designed to solve visual CAPTCHA challenges. It is published in
*"Are CAPTCHAs Still Bot-hard? Generalized Visual CAPTCHA Solving with Agentic Vision Language Model"* (USENIX Security'25).

> **Disclaimer (research only)**
> - Do not use this project to bypass CAPTCHAs on real-world services.
> - Follow ethical and legal requirements and the usage policies of any model providers you use.
> - You are solely responsible for any misuse.

## This fork: security + engineering hardening

This repo includes a security-focused refactor:
- Removed model-output `exec()` and `eval()` execution paths (RCE hardening).
- Switched Stage1/2/3 to **JSON outputs + schema validation + allowlisted executor**.
- Added a **local-only benchmark** default guard (`HALLIGAN_ALLOW_NONLOCAL_BENCHMARK=1` to override intentionally).

See `docs/SECURITY.md` and `docs/USAGE.md` for details.

## Quickstart

1) Start benchmark + browser (Docker)
```bash
docker compose up -d --build
```

2) Create Halligan env + config
```bash
cd halligan
pixi install
cp .env.example .env
```

3) (Optional) Download additional local models (large)
```bash
cd halligan
bash get_models.sh
```

## Tests

- Unit tests (no services):
```bash
cd halligan
pixi run pytest -m 'not integration' -q
```

- Integration tests (requires Docker services):
```bash
cd halligan
pixi run pytest -m integration -q
```

## Notes

- `BROWSER_URL` should match the repo root `docker-compose.yml` mapping (`ws://127.0.0.1:5001/`).
- `BENCHMARK_URL` is loaded inside the remote browser container; use `http://host.docker.internal:3334` on Docker Desktop.
