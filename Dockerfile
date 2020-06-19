FROM python:3.7-alpine

RUN pip3 install requests &&\
    pip3 install datetime &&\
    pip3 install mysql-connector-python &&\
    pip3 install config &&\
    pip3 install slack &&\
    pip3 install slackclient

WORKDIR /app

COPY API_list.txt /app

COPY config.py /app

COPY dummy_api.py /app

CMD python3 dummy_api.py
