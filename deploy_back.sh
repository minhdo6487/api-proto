cp docker/dev/back.Dockerfile Dockerfile
docker build -t test-back .
docker tag test-back so0k/golfconnect:test-back
docker push so0k/golfconnect:test-back