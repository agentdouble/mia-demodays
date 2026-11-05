FROM python:3.14-slim-trixie@sha256:af8a5aa14780025dbfbcfbc81bd8a91ebd87711dd5b0f48ed71090949dd7cb1d
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
    && groupadd -g 10001 mia && useradd -u 10001 -g mia -M -d /nonexistent mia
COPY app ./app
COPY mia/mia-recommander ./mia/mia-recommander
COPY deploy/gunicorn.conf.py ./gunicorn.conf.py
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-m", "app.healthcheck"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app.wsgi:application"]
