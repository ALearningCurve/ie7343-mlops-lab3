# ie7343-mlops-lab3

This lab submission is a modification of `Labs/Airflow_Labs/Lab_1` in the main repo.

The starter code for that lab does k-mean clustering using the elbow method to find optimal "k" to use.

It defined the the following steps:
- `load_data` to read csv
- `data_preprocessing` to preprocess the data
- `build_save_model` to build k-means, save to file, and return SSE values
- `load_model_elbow` find the optimal number of cluster via elbow method

Our submmission changes the following:
- Use extended variant of airflow container to map in dependencies using uv
- 


## Running

1. Install the [uv](https://github.com/astral-sh/uv) package manager. Following instructions assumes you have docker installed are running in linux-like environment.
2. Install deps with `uv sync`
3. Start Airflow
    - Check you have enough RAM in docker engine (at least 4G) by running `docker run --rm "debian:bullseye-slim" bash -c 'numfmt --to iec $(echo $(($(getconf _PHYS_PAGES) * $(getconf PAGE_SIZE))))'`
    - Create required folder structure with `bash setup-airflow.sh`
    - Setup and run the compose with `bash run-airflow.sh`

