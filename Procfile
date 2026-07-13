web: gunicorn --worker-class eventlet -w 1 main:app
worker: celery -A tasks.celery worker --loglevel=info