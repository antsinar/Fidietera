FROM quay.io/jupyter/base-notebook:lab-4.3.5 AS builder

WORKDIR /build

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    acl \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

RUN uv init && \
    uv add --no-cache \
    bpython \
    jupyterlab-lsp \
    'python-lsp-server[rope, pyflakes, pycodestyle, yapf, flake8, pylint]' \
    jupyterlab-language-pack-el-GR && \
    find /build/.venv -type d -name "__pycache__" -exec rm -rf {} +

FROM builder AS runner
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR "${HOME}"

RUN setfacl -R -m u:jovyan:rwx "${HOME}" && setfacl -d -m u:jovyan:rwx "${HOME}"

COPY --from=builder /build/.venv .venv

EXPOSE 8888
USER jovyan
ENTRYPOINT [ "/bin/sh", "-c", "PATH=\"${HOME}/.venv/bin:${PATH}\" jupyter lab --ip=0.0.0.0 --port=8888" ]
CMD [ ]
