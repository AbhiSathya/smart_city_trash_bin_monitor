FROM python:3.9-slim

WORKDIR /app

# Set UTF-8 encoding
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8
    
RUN pip install --no-cache-dir kafka-python

COPY . .

CMD ["python", "bin_simulator.py"]
