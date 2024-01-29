FROM python:3-slim

COPY . /app 
WORKDIR /app


RUN pip install -r requirements.txt


RUN apk update && apk add --no-cache git

ENV PYTHONPATH /app 
CMD ["python","/app/main.py"]