# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to keep the image size down
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Expose the port NiceGUI will listen on (default is 8080)
EXPOSE 8080

# Command to run the NiceGUI application
# NiceGUI can use environment variables for host and port
# App Runner will inject the PORT environment variable
CMD python nicegui_app.py --host 0.0.0.0 --port $PORT
