FROM spark:python3

WORKDIR /app

COPY requirements.txt .
USER root
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/