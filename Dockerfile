FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/QQSHI13/docsforge"
LABEL org.opencontainers.image.description="DocsForge - documentation engine with Material theme"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# System deps: TikZ toolchain (texlive + dvisvgm), PDF export (chromium for
# playwright), and curl for health checks / asset fetching.
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    texlive-latex-base \
    texlive-pictures \
    texlive-latex-extra \
    dvisvgm \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install DocsForge from local source with all extras (PDF, social cards,
# Chinese search, playwright)
COPY . /tmp/docsforge
RUN pip install --no-cache-dir "/tmp/docsforge[all]" && \
    rm -rf /tmp/docsforge && \
    playwright install chromium 2>/dev/null || true

ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium

# Run as non-root
RUN useradd --create-home --uid 1000 docsforge \
    && mkdir -p /docs && chown docsforge:docsforge /docs

USER docsforge
WORKDIR /docs
EXPOSE 8000

ENTRYPOINT ["docsforge"]
CMD ["--help"]