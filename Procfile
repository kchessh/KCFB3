web: gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 main:app
worker: celery -A tasks.celery worker --loglevel=info