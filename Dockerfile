FROM python:3.13.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright
RUN pip install --no-cache-dir playwright

# Install system dependencies for browsers (handles Debian Trixie correctly)
RUN python -m playwright install-deps

# Install browsers
RUN python -m playwright install

COPY . .

EXPOSE 5000

CMD ["python", "web_app.py"]