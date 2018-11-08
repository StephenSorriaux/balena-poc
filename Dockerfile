FROM resin/generic-armv7ahf-python:3.6-slim

ENV INITSYSTEM on

WORKDIR /usr/src
# pip install python deps from requirements.txt
# For caching until requirements.txt changes
COPY . ./
RUN apt update && \
    apt install git gcc musl-dev libc-dev && \
    pip install -r requirements.txt
CMD ["python", "-u", "balena-app.py"]