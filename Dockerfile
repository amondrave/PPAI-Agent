FROM python:3.12.8-slim AS base

RUN groupadd -r ppai && useradd -r -g ppai -d /app -s /sbin/nologin ppai

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ppai/ ppai/

RUN chown -R ppai:ppai /app
USER ppai

CMD ["python", "-m", "ppai.main"]
