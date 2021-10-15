import sys
import os
from flask import Flask, request
from datetime import datetime
import pandas as pd
import random
from decimal import Decimal

app = Flask(__name__)

@app.route('/predict-breed', methods = ['POST'])
def predict_breed_api():
    request_data = request.get_json()
    print_heroku('request JSON')
    image = None
    if request_data:
        # this is for testing, we can remove after integrate with Prem code in order to label breed
        if 'image' in request_data:
            image = request_data['image']
        else:
            return create_response('error', 400, f'image was not found')

    print_heroku(f'image url : {image}')
    breed = predict_breed(image) # PREM need to update the prediction code in this function
    return {'status': 'ok', 'breed': breed}, 200

def create_response(status, code, message):
    return {'status': status, 'message': message}, code
    
def print_heroku(message):
    print(message)
    sys.stdout.flush()

def predict_breed(image_url):
    # image_data = 1. download image fro a given url
    # transformed_data = trasnform(image_data)
    # predict(transformed_data)

    breeds = ['Beagle', 'Poodle', 'Siberian Husky', 'Pug', 'Pomeranian', 'Shih-tzu', 'Golden Retriever', 'Corgi', 'Chihuahua', 'Bangkaew']
    index = random.randint(0, 9)
    return breeds[index]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)