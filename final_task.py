from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'airflow',
}

with DAG(
    dag_id='final_converging_dag',
    default_args=default_args,
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
) as dag:

    start = DummyOperator(
        task_id='start',
    )

    branch_1 = DummyOperator(
        task_id='branch_1',
    )

    branch_2 = DummyOperator(
        task_id='branch_2',
    )

    final_task = DummyOperator(
        task_id='final_task',
    )

    start >> [branch_1, branch_2] >> final_task
