# KCF playground — self-contained image serving the open-source toolchain.
# Build context is the repository ROOT (so kcf-oss/ and semantic-core/ are both
# copied and keep their sibling relationship the tools require).
#
#   docker build -f kcf-oss/playground/Dockerfile -t kcf-playground .
#   docker run -p 8000:8000 kcf-playground
#
FROM python:3.12-slim

WORKDIR /app
COPY kcf-oss/ /app/kcf-oss/
COPY semantic-core/ /app/semantic-core/

RUN pip install --no-cache-dir -r /app/kcf-oss/playground/requirements.txt

EXPOSE 8000
# Bind the toolchain's app dir; semantic-core resolves as a sibling of kcf-oss.
CMD ["uvicorn", "app:app", "--app-dir", "/app/kcf-oss/playground", "--host", "0.0.0.0", "--port", "8000"]
