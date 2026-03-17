FROM python:3.12.8-slim AS base

RUN groupadd -r ppai && useradd -r -g ppai -d /app -s /sbin/nologin ppai

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ppai/ ppai/

RUN chown -R ppai:ppai /app
USER ppai

EXPOSE 8443

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket; s=socket.create_connection(('localhost',8443),timeout=3); s.close()" || exit 1

CMD ["python", "-m", "ppai.main"]
