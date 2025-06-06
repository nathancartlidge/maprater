FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y
RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
