FROM python:3.10-alpine


RUN apk update
RUN adduser myuser -D

WORKDIR /home/myuser/app
COPY ./app .

RUN pip install -r requirements.txt

RUN chown -R myuser:myuser /home/myuser/app

USER myuser

CMD python3 main.py
