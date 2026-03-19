FROM spark:python3

WORKDIR /app

COPY requirements.txt .
USER root
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENV PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/*
ENV PATH="/opt/spark/bin:${PATH}"