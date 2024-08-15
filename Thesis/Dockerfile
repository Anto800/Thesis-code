FROM python:3.8-slim

WORKDIR /app

COPY app.py /app

# Install Flask and Prometheus client library
RUN pip install flask prometheus_client

EXPOSE 5000

CMD ["python", "app.py"]
