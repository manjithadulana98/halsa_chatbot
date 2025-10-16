# Use an official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy your project files into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Railway expects
EXPOSE 8080

# Run FastAPI using Uvicorn
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080"]
