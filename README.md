# spark
Dedicated repo to replicate how spark would work in production.

# Docker Commands
```docker
docker build -t spark -f docker/Dockerfile .
docker run -it --name my_container spark /bin/bash 
exit # to quit container
```
Verification steps for env
```
which spark-submit
spark-submit --version
pyspark
spark-submit test_spark.py
```