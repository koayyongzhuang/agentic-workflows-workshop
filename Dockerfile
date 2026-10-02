FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY workshop ./workshop
COPY part1_single_agent ./part1_single_agent
COPY part2_multi_agent ./part2_multi_agent
COPY scripts ./scripts
RUN pip install -e ".[all,dev]"

COPY . .
CMD ["bash"]
