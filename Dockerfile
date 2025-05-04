# Use lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy app files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port your app runs on
EXPOSE 5000

# Run the Flask app via gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
