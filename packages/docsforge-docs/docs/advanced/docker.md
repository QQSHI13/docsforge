# Docker Image

DocsForge can be run inside a Docker container for isolated, reproducible documentation builds.

## Quick Start

```bash
# Pull the latest image
docker pull ghcr.io/qqshi13/docsforge:latest

# Build your docs
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest build

# Start dev server (visit http://localhost:8000)
docker run --rm -v $(pwd):/docs -p 8000:8000 ghcr.io/qqshi13/docsforge:latest serve --lan

# Export PDF
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest build --pdf

# Validate config
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest check

# Auto-fix common config issues
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest check --fix
```

## Available Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `11.0.4` | Specific version |
| `sha-abc123` | Specific commit SHA |
| `11.0` | Latest 11.0.x release |

Images are published to `ghcr.io/qqshi13/docsforge` automatically on every GitHub release.

## What's Included

The Docker image (~1.5GB) includes:

- **DocsForge** with all extras (`docsforge[all]`)
- **Playwright + Chromium** for PDF export
- **TeXLive + dvisvgm** for TikZ diagram compilation
- **Python 3.12** runtime

## Building Locally

```dockerfile
FROM python:3.12-slim

RUN pip install docsforge

WORKDIR /docs
EXPOSE 8000

ENTRYPOINT ["docsforge"]
CMD ["--help"]
```

```bash
docker build -t my-docsforge .
docker run --rm -v $(pwd):/docs my-docsforge build
```

## Docker Compose

```yaml
# docker-compose.yml
version: '3'
services:
  docs:
    image: ghcr.io/qqshi13/docsforge:latest
    command: serve --lan
    ports:
      - "8000:8000"
    volumes:
      - .:/docs
```

```bash
docker-compose up
```

## CI/CD Integration

Use the Docker image in CI pipelines for reproducible builds:

```yaml
# .github/workflows/docs.yml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Build docs
        run: |
          docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest build
      - name: Deploy
        run: |
          # upload site/ to your hosting provider
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE` | Path to a Chromium/Chrome binary for PDF export. If unset, DocsForge probes common Linux paths (`/usr/bin/chromium`, `/usr/bin/google-chrome`, …) and finally falls back to Playwright's bundled browser. |

## Customizing the PDF Browser

PDF export (`docsforge build --pdf`) launches a headless Chromium via Playwright.
The image ships Chromium at `/usr/bin/chromium` and points `PLAYWRIGHT_CHROMIUM_EXECUTABLE`
at it. To use a different browser:

**Override the path** (the file must exist *inside* the container):
```bash
docker run --rm -v "$PWD:/docs" \
  -e PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/google-chrome-stable \
  ghcr.io/qqshi13/docsforge:latest build --pdf
```

**Use Playwright's own bundled browser** (uninstall the env override so it falls
back through the default probe list to Playwright's managed download — already
installed in the image via `playwright install chromium`):
```bash
docker run --rm -v "$PWD:/docs" \
  -e PLAYWRIGHT_CHROMIUM_EXECUTABLE= \
  ghcr.io/qqshi13/docsforge:latest build --pdf
```

**Mount a host browser binary** read-only and point at it:
```bash
docker run --rm -v "$PWD:/docs" \
  -v /usr/bin/google-chrome:/usr/bin/host-chrome:ro \
  -e PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/host-chrome \
  ghcr.io/qqshi13/docsforge:latest build --pdf
```

Tune parallelism with `--jobs`:
```bash
docker run --rm -v "$PWD:/docs" ghcr.io/qqshi13/docsforge:latest build --pdf --jobs 2
```
