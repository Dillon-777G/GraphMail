# Use the official Python image as the base
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.in /app/requirements.in
RUN pip install --no-cache-dir -r /app/requirements.in

# Copy the rest of the application code
COPY . /app

# Expose the application port
EXPOSE 5000

# Command to run the FastAPI application
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "5000"]
