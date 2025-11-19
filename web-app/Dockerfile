#use a lightweight Python image
FROM python:3.10-slim

#prevent Python from writing .pyc files and buffer logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

#set work directory inside the container
WORKDIR /app

#install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#copy the rest of the app code
COPY . .

#flask app listens on port 3000
EXPOSE 5000

#run the web app
CMD ["python", "app.py"]
