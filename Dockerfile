# Dockerize Python Flask app and deploy to Heroku
# https://medium.com/analytics-vidhya/dockerize-your-python-flask-application-and-deploy-it-onto-heroku-650b7a605cc9

FROM python:3.7.9-buster
COPY . /app
WORKDIR /app
COPY docker-requirements.txt .
RUN pip install -r docker-requirements.txt
CMD ["python", "app.py"]