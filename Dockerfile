# Use official Python slim image
FROM python:3.10-slim

# Install system dependencies required by Playwright browsers
RUN apt-get update && apt-get install -y \
    libgtk-4-1 libgraphene-1.0-0 libgstreamer-gl1.0-0 libgstreamer-plugins-base1.0-0 \
    libenchant-2-2 libsecret-1-0 libmanette-0.2-0 libgles2-mesa \
    libx11-xcb-dev libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libcups2 \
    libpango-1.0-0 libatk1.0-0 libnss3 wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and required browsers
RUN pip install --no-cache-dir playwright
RUN playwright install

# Copy the rest of your application code
COPY . .

# Expose the port your Flask app will run on
EXPOSE 5000

# Command to run your Flask app, adjust if your app file or run command differs
CMD ["python", "web_app.py"]
