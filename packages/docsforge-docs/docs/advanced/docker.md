# Docker Image

DocsForge can be run inside a Docker container for isolated, reproducible documentation builds.

## Quick Start

```bash
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge build
docker run --rm -v $(pwd):/docs -p 8000:8000 ghcr.io/qqshi13/docsforge serve
```

## Building the Image

```dockerfile
FROM python:3.12-slim

RUN pip install docsforge

WORKDIR /docs
EXPOSE 8000

ENTRYPOINT ["docsforge"]
CMD ["--help"]
```

Build and run:

```bash
docker build -t docsforge .
docker run --rm -v $(pwd):/docs docsforge build
docker run --rm -v $(pwd):/docs -p 8000:8000 docsforge serve
```

## With PDF Support

For `docsforge build --pdf`, you need Playwright and Chromium:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    && rm -rf /var/lib/apt/lists/*

RUN pip install docsforge[pdf] && \
    playwright install chromium

ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium
WORKDIR /docs
EXPOSE 8000

ENTRYPOINT ["docsforge"]
CMD ["--help"]
```

## With TikZ Support

For TikZ diagrams, add LaTeX:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base texlive-pictures texlive-latex-extra \
    dvisvgm \
    && rm -rf /var/lib/apt/lists/*
```

## Docker Compose

```yaml
version: '3'
services:
  docs:
    image: ghcr.io/qqshi13/docsforge
    command: serve --lan
    ports:
      - "8000:8000"
    volumes:
      - .:/docs
```
