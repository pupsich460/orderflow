FROM python:3.12-slim

WORKDIR /app

COPY notifier/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY notifier/app/ .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]