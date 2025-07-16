# Use an official lightweight Python image
FROM python:3.10-slim

# Set environment variables for better Python performance in Docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
# This leverages Docker's layer caching for faster builds
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's source code
# The .dockerignore file will prevent unnecessary files from being copied
COPY . .

# Expose the port the app will run on.
# DigitalOcean's App Platform will automatically set the PORT environment variable.
EXPOSE 8080

# The command to run your application using uvicorn
# We run it directly, bypassing the local run_api.py script.
# The host 0.0.0.0 is required to make the app accessible from outside the container.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "60"] 