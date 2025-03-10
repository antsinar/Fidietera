FROM quay.io/jupyter/base-notebook:lab-4.3.5 AS builder
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*
USER ${NB_UID}
RUN pip wheel --wheel-dir /usr/src/wheels \
    bpython \
    jupyterlab-lsp \
    'python-lsp-server[all]'

FROM builder AS runner
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
WORKDIR "${HOME}"
COPY --from=builder /usr/src/wheels /wheels/
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
    && rm -rf /wheels/
EXPOSE 8888
CMD ["jupyter", "lab"]