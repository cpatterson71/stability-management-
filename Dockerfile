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

# When the container launches, run app.py with streamlit.
# - server.port $PORT: Use the port provided by the App Runner environment variable.
# - server.address 0.0.0.0: Listen on all network interfaces, making it accessible from outside the container.
# - server.headless true: Run in headless mode, appropriate for a server.
# - server.enableCORS false / server.enableXsrfProtection false: Recommended settings when running behind a proxy like App Runner.
CMD ["streamlit", "run", "app.py", "--server.port", "$PORT", "--server.address", "0.0.0.0", "--server.headless", "true", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
