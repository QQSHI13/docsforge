FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/QQSHI13/docsforge"
LABEL org.opencontainers.image.description="DocsForge - documentation engine with Material theme"
LABEL org.opencontainers.image.licenses="LGPL-3.0-or-later"

# Install system deps for Playwright, TikZ, and common tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    texlive-latex-base texlive-pictures texlive-latex-extra \
    dvisvgm \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install DocsForge with all extras
RUN pip install --no-cache-dir "docsforge[all]" && \
    playwright install chromium 2>/dev/null || true

ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium
WORKDIR /docs
EXPOSE 8000

ENTRYPOINT ["docsforge"]
CMD ["--help"]
