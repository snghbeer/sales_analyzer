# Use the official Python image as the base image
FROM python:3-slim

# Set the working directory inside the container
WORKDIR /app

COPY requirements.txt .

# Install the Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80

CMD ["gunicorn", "-b", "0.0.0.0:80", "index:app"]

