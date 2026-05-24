FROM docker.io/library/python:3.13-slim

ENV \
    DEBCONF_NONINTERACTIVE_SEEN="true" \
    DEBIAN_FRONTEND="noninteractive"

ENV \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    IS_DOCKER=True

WORKDIR /app

COPY requirements.txt ./
COPY intel-gpu-exporter.py ./

RUN \
    apt-get update \
    && \
    apt-get install --no-install-recommends -y \
        catatonit \
        intel-gpu-tools \
    && pip install --require-hashes --requirement requirements.txt \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf \
        /tmp/* \
        /var/lib/apt/lists/* \
        /var/cache/apt/* \
        /var/tmp/*

ENTRYPOINT ["/usr/bin/catatonit", "--", "/usr/local/bin/python"]
CMD ["/app/intel-gpu-exporter.py"]

LABEL \
    org.opencontainers.image.title="intel-gpu-exporter" \
    org.opencontainers.image.source="https://github.com/slother/intel-gpu-exporter"
