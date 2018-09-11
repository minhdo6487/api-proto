cp docker/dev/celery.Dockerfile Dockerfile
docker build -t test-celery .
docker tag test-celery so0k/golfconnect:test-celery
docker push so0k/golfconnect:test-celery