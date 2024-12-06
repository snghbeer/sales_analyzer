.venv\Scripts\activate

pip freeze > requirements.txt

docker buildx build -t analyzer:latest .

docker run -p 5000:80 analyzer

docker tag 7fbbb18a1c9a snghbeer/nivon:analyzer

docker push snghbeer/nivon:analyzer