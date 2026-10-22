FROM python:3.10-slim-trixie

WORKDIR /usr/app

COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /bin/uv

COPY pyproject.toml uv.lock .python-version ./

RUN mkdir logs

RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-dev --no-cache \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    && apt-get install -y unixodbc \
    unixodbc-dev \
    tdsodbc \
    freetds-dev \
    freetds-bin \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/* \
    && odbcinst -i -d -f /usr/share/tdsodbc/odbcinst.ini

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
