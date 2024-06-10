ARG OPEN_DEVIN_BUILD_VERSION=dev
FROM node:21.7.2-bookworm-slim as frontend-builder

WORKDIR /app

COPY ./frontend/package.json frontend/package-lock.json ./
RUN npm install -g npm@10.5.1
RUN npm ci

COPY ./frontend ./
RUN npm run make-i18n && npm run build

FROM python:3.12.3-slim as backend-builder

WORKDIR /app
ENV PYTHONPATH '/app'

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN apt-get update -y \
    && apt-get install -y curl make git build-essential g++ \
    && python3 -m pip install poetry==1.8.2  --break-system-packages

COPY ./pyproject.toml ./poetry.lock ./
RUN touch README.md
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# Install litellm module
RUN python3 -m pip install litellm

# Install python-docx module
RUN python3 -m pip install python-docx

FROM python:3.12.3-slim as runtime

WORKDIR /app

ENV RUN_AS_DEVIN=true
# A random number--we need this to be different from the user's UID on the host machine
ENV OPENDEVIN_USER_ID=42420
ENV USE_HOST_NETWORK=false
ENV SSH_HOSTNAME=host.docker.internal
ENV WORKSPACE_BASE=/opt/workspace_base
ENV OPEN_DEVIN_BUILD_VERSION=$OPEN_DEVIN_BUILD_VERSION
RUN mkdir -p $WORKSPACE_BASE

RUN apt-get update -y \
    && apt-get install -y curl ssh sudo g++

RUN sed -i 's/^UID_MIN.*/UID_MIN 499/' /etc/login.defs # Default is 1000, but OSX is often 501
RUN sed -i 's/^UID_MAX.*/UID_MAX 1000000/' /etc/login.defs # Default is 60000, but we've seen up to 200000

RUN groupadd app
RUN useradd -l -m -u $OPENDEVIN_USER_ID -s /bin/bash opendevin && \
    usermod -aG app opendevin && \
    usermod -aG sudo opendevin && \
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
RUN chown -R opendevin:app /app && chmod -R 770 /app
RUN sudo chown -R opendevin:app $WORKSPACE_BASE && sudo chmod -R 770 $WORKSPACE_BASE
USER opendevin

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH='/app'

COPY --chown=opendevin:app --chmod=770 --from=backend-builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
RUN playwright install --with-deps chromium

COPY --chown=opendevin:app --chmod=770 ./opendevin ./opendevin
COPY --chown=opendevin:app --chmod=777 ./opendevin/runtime/plugins ./opendevin/runtime/plugins
COPY --chown=opendevin:app --chmod=770 ./agenthub ./agenthub

# Install python-docx module in runtime stage
RUN python3 -m pip install python-docx

# Install PyPDF2 module in runtime stage
RUN python3 -m pip install PyPDF2

# Install python-pptx module in runtime stage
RUN python3 -m pip install python-pptx

# Install pylatexenc module in runtime stage
RUN python3 -m pip install pylatexenc

# Install chromadb module in runtime stage
RUN python3 -m pip install chromadb

# Install llama_index and its dependencies in runtime stage
RUN python3 -m pip install llama_index llama_index_vector_stores_chroma chromadb llama_index_embeddings_huggingface torch llama_index_embeddings_azure_openai llama_index_embeddings_ollama

# Install pydantic package in runtime stage
RUN python3 -m pip install pydantic==2.7.3

# Patch pydantic package to fix TypeError related to ForwardRef._evaluate() for Python 3.12.4 compatibility
RUN sed -i 's/def evaluate_forwardref(type_: ForwardRef, globalns: Any, localns: Any) -> Any:/def evaluate_forwardref(type_: ForwardRef, globalns: Any, localns: Any) -> Any:\
    return cast(Any, type_)._evaluate(globalns, localns, set(), recursive_guard=set())/' /usr/local/lib/python3.10/dist-packages/pydantic/v1/typing.py

RUN python opendevin/core/download.py # No-op to download assets
RUN chown -R opendevin:app /app/logs && chmod -R 770 /app/logs # This gets created by the download.py script

COPY --chown=opendevin:app --chmod=770 --from=frontend-builder /app/dist ./frontend/dist
COPY --chown=opendevin:app --chmod=770 ./containers/app/entrypoint.sh /app/entrypoint.sh

USER root

WORKDIR /app

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "opendevin.server.listen:app", "--host", "0.0.0.0", "--port", "3000"]
