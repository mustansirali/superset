FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/webhook_automation/

EXPOSE 8000

CMD ["python", "-m", "webhook_automation"]
