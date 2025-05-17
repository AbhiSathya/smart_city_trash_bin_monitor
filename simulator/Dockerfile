FROM python:3.9-slim

WORKDIR /app

# Set UTF-8 encoding
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8

COPY . .


RUN pip install -r requirements.txt


CMD ["python", "bin_simulator.py"]
