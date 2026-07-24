# KCF MCP server — remote (HTTP) deployment, e.g. for a hosted ChatGPT connector.
# Build context is the repository ROOT (so kcf-oss/ and semantic-core/ are copied
# with their sibling relationship).
#
#   docker build -f kcf-oss/mcp/Dockerfile -t kcf-mcp .
#   docker run -p 8000:8000 kcf-mcp        # streamable-http MCP endpoint on :8000
#
FROM python:3.12-slim

WORKDIR /app
COPY kcf-oss/ /app/kcf-oss/
COPY semantic-core/ /app/semantic-core/

RUN pip install --no-cache-dir -r /app/kcf-oss/mcp/requirements.txt

# Remote transport, bound so it is reachable from outside the container.
ENV KCF_MCP_TRANSPORT=streamable-http \
    KCF_MCP_HOST=0.0.0.0 \
    KCF_MCP_PORT=8000

EXPOSE 8000
CMD ["python", "/app/kcf-oss/mcp/server.py"]
