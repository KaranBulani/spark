FROM bitnami/spark:3.5

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/