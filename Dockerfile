FROM ubuntu:latest

RUN apt-get update
RUN apt install -y python3-pip
RUN apt-get clean

RUN mkdir /Sbotify
RUN mkdir /Sbotify/data
RUN mkdir /Sbotify/secret

WORKDIR /Sbotify

COPY src src
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "src/site/app.py"]
