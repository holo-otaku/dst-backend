FROM python:3.10.8 as build

WORKDIR /usr/app
RUN python -m venv /usr/app/venv
ENV PATH="/usr/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

FROM python:3.10.8-alpine3.17
WORKDIR /usr/app
COPY --from=build /usr/app/venv ./venv
COPY /app .

ENV PATH="/usr/app/venv/bin:$PATH"
CMD [ "python", "app.py" ]