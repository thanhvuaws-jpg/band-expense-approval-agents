FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e . 2>/dev/null || pip install --no-cache-dir \
    band-sdk langgraph langchain langchain-openai flask python-dotenv httpx

COPY . .

RUN mkdir -p /data
