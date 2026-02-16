# Import necessary libraries and modules
from airflow import DAG

# from airflow.operators.python import PythonOperator
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
from src.lab import (
    ingress_data,
    load_data,
    data_preprocessing,
    build_save_model,
    load_evaluate_model,
)


# Define default arguments for your DAG
default_args = {
    "owner": "Will WS",
    "start_date": datetime(2026, 1, 15),
    "retries": 0,  # Number of retries in case of task failure
    "retry_delay": timedelta(minutes=5),  # Delay before retries
}

# Create a DAG instance named 'Airflow_Lab1' with the defined default arguments
with DAG(
    "Data-Preprocessing-and-Regressor-Training",
    default_args=default_args,
    description="Sample DAG which take in data csv, creates train/test split, and then outputs the best result",
    catchup=False,
) as dag:
    ingress_data_task = PythonOperator(
        task_id="ingress_data_task",
        python_callable=ingress_data,
    )

    # Task to load data, calls the 'load_data' Python function
    load_data_task = PythonOperator(
        task_id="load_data_task",
        python_callable=load_data,
    )

    # Task to perform data preprocessing, depends on 'load_data_task'
    data_preprocessing_task = PythonOperator(
        task_id="data_preprocessing_task",
        python_callable=data_preprocessing,
        op_args=[load_data_task.output],
    )

    # Task to build and save a model, depends on 'data_preprocessing_task'
    build_save_model_task = PythonOperator(
        task_id="build_save_model_task",
        python_callable=build_save_model,
        op_args=[data_preprocessing_task.output, "model.sav"],
    )

    # Task to load a model using the 'load_model_elbow' function, depends on 'build_save_model_task'
    load_model_task = PythonOperator(
        task_id="load_model_evaluate_task",
        python_callable=load_evaluate_model,
        op_args=["model.sav", build_save_model_task.output],
    )

    # Set task dependencies
    (
        ingress_data_task
        >> load_data_task
        >> data_preprocessing_task
        >> build_save_model_task
        >> load_model_task
    )  # type: ignore

# If this script is run directly, allow command-line interaction with the DAG
if __name__ == "__main__":
    dag.test()
