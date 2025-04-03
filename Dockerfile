# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 9000 for FastAPI
EXPOSE 9000

# Command to run the FastAPI app
CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "9000"]
