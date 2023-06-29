FROM python:3.10.8

WORKDIR /usr/app
RUN python -m venv /usr/app/venv
ENV PATH="/usr/app/venv/bin:$PATH"

COPY /app ./app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
RUN apt-get update && apt-get install -y tdsodbc unixodbc-dev \
    && apt install unixodbc -y  \
    && apt install freetds-dev -y  \
    && apt install freetds-bin -y  \
    && apt-get clean -y

RUN odbcinst -i -d -f /usr/share/tdsodbc/odbcinst.ini
ENV FLASK_APP=app/app.py
COPY /migrations ./migrations

CMD [ "python", "app/app.py" ]