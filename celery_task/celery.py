from celery import Celery

broker = 'redis://127.0.0.1:6379/1'
backend = 'redis://127.0.0.1:6379/2'
app = Celery(broker=broker, backend=backend, include=['celery_task.tasks'])