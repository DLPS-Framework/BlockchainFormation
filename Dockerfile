FROM python:3.8-buster

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_REGION

COPY . /app
WORKDIR /app

RUN python3.8 -m pip install .
RUN python3.8 -mpip install toml

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

RUN export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
RUN export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
RUN (echo $AWS_ACCESS_KEY_ID; echo $AWS_SECRET_ACCESS_KEY; echo $AWS_REGION; echo) | aws configure

