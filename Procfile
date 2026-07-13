web: gunicorn --worker-class eventlet -w 1 app:application
worker: celery -A tasks.celery worker --loglevel=info