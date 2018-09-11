FROM python:3.4.7-alpine

LABEL maintainer = "Phuong <htphuong290@gmail.com>"

RUN apk add --no-cache \
  bash \
  supervisor \
  linux-headers \
  gcc \
  musl-dev \
  postgresql-dev \
  alpine-sdk \
  git \
  tzdata \
  pcre-dev \
  && cat /usr/share/zoneinfo/Asia/Saigon > /etc/localtime \
  && pip install uWSGI

RUN mkdir /code
WORKDIR /code

ADD requirements.txt /code/requirements.txt
RUN pip install -r requirements.txt

# add & install requirements before add code for better caching
ADD . /code/

RUN git rev-parse --verify HEAD > version

COPY ./devops_config/supervisor.ini /etc/supervisor.d/

CMD ["supervisord", "-n"]
