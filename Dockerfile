FROM alpine:latest

RUN apk add --update --no-cache python3
RUN python3 -m ensurepip

RUN mkdir /Sbotify
RUN mkdir /Sbotify/data
RUN mkdir /Sbotify/secret

WORKDIR /Sbotify

COPY src src
COPY requirements.txt requirements.txt

RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["python3", "src/site/app.py"]