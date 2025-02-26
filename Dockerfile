FROM python:3.10-alpine


RUN apk update
RUN adduser myuser -D

WORKDIR /home/myuser/app
COPY ./app .

RUN pip install --no-cache-dir -r requirements.txt

RUN chown -R myuser:myuser /home/myuser/app
RUN chmod -R 777 /home/myuser/app

USER myuser

CMD python3 main.py
