from celery import Celery

broker = 'redis://127.0.0.1:6378/1'
backend = 'redis://127.0.0.1:6378/2'
app = Celery(broker=broker, backend=backend, include=['celery_task.tasks'])