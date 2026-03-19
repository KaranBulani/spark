# Spark Redaction POC

This repo is a local-first Spark POC for data redaction by using Python and Google Sensitive Data Protection (Cloud DLP) format-preserving encryption.

The current implementation supports two modes:

- `local`: a reversible format-preserving demo cipher so the job can run offline on a laptop or inside the container without GCP credentials.
- `gcp`: a Google DLP table-FPE scaffold that is ready for you to connect to real credentials, keys, and BigQuery tables later.

## Repo Flow

1. `src/readers/data_reader.py` holds the hardcoded demo values and records.
2. `src/dlp/dlp_client.py` encrypts and decrypts the chosen field.
3. `src/spark_jobs/redact_job.py` runs the demo, checks that repeated input gives repeated encrypted output, and prints a JSON summary.
4. `src/writers/data_writer.py` is a placeholder for the future BigQuery write path.

## Local Config

`configs/local.yaml` is runnable as-is.

It uses:

- Spark in local mode: `local[*]`
- Local reversible demo cipher
- `customer_ref` as the redacted field

## Dev And Prod Configs

`configs/dev.yaml` and `configs/prod.yaml` now mirror the same simple local demo shape with different environment names.

## Docker

Build the image:

```bash
docker build -t spark-redaction-poc -f docker/Dockerfile .
```

Start an interactive container:

```bash
docker run --rm -it -v "${PWD}:/app" spark-redaction-poc /bin/bash
```

The current `docker/Dockerfile` copies only `src/` into the image, so mounting the repo is the easiest way to make the `configs/` files available at runtime.

## Run The Sample Job

From the repo root:

```bash
python -m src.spark_jobs.redact_job --config configs/local.yaml
```

Or with Spark submit:

```bash
spark-submit src/spark_jobs/redact_job.py --config configs/local.yaml
```

If you want the job to pick the environment file by name, this also works:

```bash
python -m src.spark_jobs.redact_job --env local
```

## Expected Output

The job prints a JSON summary that includes:

- original values
- encrypted values
- decrypted values
- repeated-value checks that show same input gives same encrypted output
- Spark app details
- input and result records

## Tests

Run the unit tests with:

```bash
pytest -q
```

## Notes For The Next Step

- The BigQuery read and write functions are intentionally stubbed with commented Spark BigQuery examples.
- The local cipher is only for development convenience. For real redaction, use `dlp.backend: gcp` and wire in a valid wrapped or unwrapped AES key.
- A small future folder improvement would be to add a dedicated config loader module such as `src/utils/config_loader.py` once the project grows beyond this POC.
