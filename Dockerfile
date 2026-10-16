FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY workshop ./workshop
COPY lab_1_single_agent ./lab_1_single_agent
COPY lab_2_multi_agent ./lab_2_multi_agent
COPY lab_3_deep_agent ./lab_3_deep_agent
COPY scripts ./scripts
RUN pip install -e ".[all,dev]"

# Lab 4: Hermes Agent (Nous Research), in its own virtual environment so its
# dependencies never clash with the labs'. Pinned so everyone gets the same version.
RUN python -m venv /opt/hermes \
 && /opt/hermes/bin/pip install "hermes-agent[web,mcp,pty,cron,cli]==0.19.0" \
 && ln -s /opt/hermes/bin/hermes /usr/local/bin/hermes

# The Hermes dashboard's chat runs Hermes's terminal UI, which needs Node.js 22.
# Copied from the official Node image, which matches this machine's CPU (Intel or Apple silicon).
COPY --from=docker.io/library/node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
RUN apt-get update \
 && apt-get install -y --no-install-recommends libstdc++6 \
 && rm -rf /var/lib/apt/lists/* \
 && node --version

COPY . .
CMD ["bash"]
