FROM python:3.10.8-slim

WORKDIR /usr/app

COPY Pipfile* ./

RUN mkdir logs

RUN pip install --upgrade pip \
    && pip install pipenv \
    && pipenv install --system --deploy --ignore-pipfile \
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

CMD ["pipenv", "run", "flask", "run", "--host=0.0.0.0"]
