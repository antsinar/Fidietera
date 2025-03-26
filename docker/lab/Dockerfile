FROM quay.io/jupyter/base-notebook:lab-4.3.5 AS builder

USER root

RUN mamba install --yes 'bpython' \
    'jupyterlab-lsp' \
    'python-lsp-server[rope, pyflakes, pycodestyle, yapf, flake8, pylint]' \
    'jupyterlab-language-pack-el-GR' && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

FROM builder AS runner
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR "${HOME}"

EXPOSE 8888
USER ${NB_USER}
COPY ./jupyter_server_config.py ${HOME}/.jupyter/jupyter_server_config.py
ENTRYPOINT [ "/bin/sh", "-c", "jupyter lab"]
CMD [  ]
