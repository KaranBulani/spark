FROM spark:python3

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/