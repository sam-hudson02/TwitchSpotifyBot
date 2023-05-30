FROM alpine:latest

RUN apk add --update --no-cache python3
RUN python3 -m ensurepip
RUN apk add --update nodejs npm

RUN mkdir /Sbotify
RUN mkdir /Sbotify/data
RUN mkdir /Sbotify/secret

WORKDIR /Sbotify

COPY src src
COPY prisma prisma
COPY requirements.txt requirements.txt

RUN pip3 install --no-cache-dir -r requirements.txt
RUN prisma generate

CMD ["sh","-c", "prisma migrate deploy && python3 src/server.py"]
