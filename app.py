import os
from flask import Flask, flash, request, render_template
from datetime import datetime
import pandas as pd
import pickle
import random
import json 
import geopy
from geopy import distance

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import api_key
import firestore_collection

RADIUS = 5 ## unit is KM

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

app = Flask(__name__)

@app.route('/')
def home():
    return 'API is running'

@app.route('/register', methods = ['POST'])
def register_api():
    request_data = request.get_json()

    customer_id = None
    owner_name = None
    display_name = None
    image = None
    dog_name = None
    dog_age = None
    dog_gender = None
    breed = None    

    if request_data:
        if api_key.CUSTOMER_ID in request_data:
            customer_id = request_data[api_key.CUSTOMER_ID]
        else:
            return f'{api_key.CUSTOMER_ID} was not found', 400

        if api_key.OWNER_NAME in request_data:
            owner_name = request_data[api_key.OWNER_NAME]
        else:
            return f'{api_key.OWNER_NAME} was not found', 400

        if api_key.DOG_AGE in request_data:
            r_dog_age = request_data[api_key.DOG_AGE]
            l_ages = r_dog_age.split('-')
            dog_age = (int(l_ages[0]) * 12) + int(l_ages[1])
            print(f'dog age : {dog_age}')
        else:
            return f'{api_key.DOG_AGE} was not found', 400

        if api_key.DOG_GENDER in request_data:
            dog_gender = request_data[api_key.DOG_GENDER]
        else:
            return f'{api_key.DOG_GENDER} was not found', 400

        if api_key.DISPLAY_NAME in request_data:
            display_name = request_data[api_key.DISPLAY_NAME]

        if api_key.IMAGE in request_data:
            image = request_data[api_key.IMAGE]
        else:
            return f'{api_key.IMAGE} was not found', 400

        if api_key.DOG in request_data:
            dog_name = request_data[api_key.DOG].lower()
        else:
            return f'{api_key.DOG} was not found', 400

        if api_key.BREED in request_data:            
            raw_breed = request_data[api_key.BREED]
            breed = map_breed(raw_breed)
            if breed == 'error':
                return f'{raw_breed} does not support, please check spelling', 400

            print(f'English breed : {breed}')
            thai_breed = map_breed(breed, True)
            print(f'Thai breed : {thai_breed}')
            type_breed = type(thai_breed)
            print(f'type of thai breed : {type_breed}')
        else:
            return f'{api_key.BREED} was not found', 400
        
    customer = {
        'display_name': display_name,
        'owner_name': owner_name,
    }
    print(request_data)
    db.collection(firestore_collection.REGISTER).document(customer_id).set(customer) ## add or update the user profile   
    dogs = db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).where('name', '==', dog_name).get()
    print(f'dogs.length : {len(dogs)}')

    if len(dogs) > 0:
        return f'{dog_name} was already register', 200

    db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).add(
    {
            'name': dog_name,
            'breed': breed,
            'image': image,
            'age': dog_age,
            'gender': dog_gender,
            #'location': location,
            'is_informed': False,
            'datetime': datetime.now(),
    })

    return f'Successfully register {dog_name} to our system'

@app.route('/get-dogs/<customer_id>')
def get_dogs_api(customer_id):
    customer = db.collection(firestore_collection.REGISTER).document(customer_id).get()
    if not customer.exists:
        return f'customer_id : {customer_id} was not exists', 404    

    print(f'customer_id : {customer_id}')
    docs = db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).stream() # get all
    # docs = db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).where('is_informed', '==', False).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()        
        print(f'{doc.id} => {data}')
        # location = data['location']
        # print(f'lat => {location.latitude}')
        # print(f'long => {location.longitude}')
        results.append({
            "dog_id": doc.id,
            "name": data['name'],
            "breed": data['breed'],
            "image": data['image'],
            "age": data['age'],
            "gender": data['gender'],
            # "lat": location.latitude,
            # "long": location.longitude,
        })

    return {'status': 'OK', 'results': results}, 200

def add_dog_to_lost(customer, dog):
    owner_doc = db.collection(firestore_collection.REGISTER).document(customer['customer_id']) 
    db.collection(firestore_collection.LOST).document(customer['customer_id']).collection(firestore_collection.LOST_DOGS).add({
        'name': dog['name'],
        'breed': dog['breed'],
        'image': dog['image'],
        'location': dog['location'],
        'age': dog['age'],
        'gender': dog['gender'],
        'is_found': False,
        'datetime': datetime.now(),
        'owner': owner_doc,
    })

    # remove customer id as we don't need this field
    del customer['customer_id']
    # update customer info in register table
    owner_doc.update(customer)

@app.route('/lost-preregister', methods = ['POST'])
def lostpreregister_api():
    request_data = request.get_json()
    customer_id = None
    phone = None
    dog_id = None
    location = None
    lat = None
    long = None


    if request_data:
        if api_key.CUSTOMER_ID in request_data:
            customer_id = request_data[api_key.CUSTOMER_ID]
        else:
            return f'{api_key.CUSTOMER_ID} was not found', 400
        
        if api_key.PHONE in request_data:
            phone = request_data[api_key.PHONE]
        else:
            return f'{api_key.PHONE} was not found', 400

        if api_key.LOCATION in request_data:
            lat = request_data[api_key.LOCATION]['lat']
            long = request_data[api_key.LOCATION]['long']
            location= firestore.GeoPoint(lat, long)            
        else:
            return f'{api_key.LOCATION} was not found', 400

        if api_key.DOG_ID in request_data:
            dog_id = request_data[api_key.DOG_ID]
        else:
            return f'{api_key.DOG_ID} was not found', 400

    # get dog from register collection
    doc = db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).document(dog_id).get()
    if not doc.exists:
        return f'dog_id {dog_id} was not found', 404

    print(doc.to_dict())

    dog = doc.to_dict()    
    dog_name = dog['name']
    dogs = db.collection(firestore_collection.LOST).document(customer_id).collection(firestore_collection.LOST_DOGS).where('name', '==', dog_name).where('is_found', '==', False).get()
    print(f'dogs.length : {len(dogs)}')

    if len(dogs) > 0:
        return f'{dog_name} was already declared as lost', 200
    
    dog['location'] = location
    customer = {
        'customer_id': customer_id,
        'phone': phone,
    }
    add_dog_to_lost(customer, dog)

    matchDf = scan_dogs(dog, firestore_collection.FOUND_DOGS)
    result = matchDf.to_dict('records')
    return json.dumps(result, indent=4), 200

## for the case we don't do the pre-register before
@app.route('/lost-register', methods = ['POST'])
def lost_api():
    request_data = request.get_json()

    customer_id = None
    owner_name = None
    display_name = None
    image = None
    dog_name = None
    dog_gender = None
    dog_age = None
    breed = None
    lat = None
    long = None
    location = None

    if request_data:
        if api_key.CUSTOMER_ID in request_data:
            customer_id = request_data[api_key.CUSTOMER_ID]
        else:
            return f'{api_key.CUSTOMER_ID} was not found', 400

        if api_key.OWNER_NAME in request_data:
            owner_name = request_data[api_key.OWNER_NAME]
        else:
            return f'{api_key.OWNER_NAME} was not found', 400

        if api_key.PHONE in request_data:
            phone = request_data[api_key.PHONE]
        else:
            return f'{api_key.PHONE} was not found', 400

        if api_key.DISPLAY_NAME in request_data:
            display_name = request_data[api_key.DISPLAY_NAME]

        if api_key.IMAGE in request_data:
            image = request_data[api_key.IMAGE]
        else:
            return f'{api_key.IMAGE} was not found', 400

        if api_key.DOG in request_data:
            dog_name = request_data[api_key.DOG].lower()
        else:
            return f'{api_key.DOG} was not found', 400

        if api_key.DOG_GENDER in request_data:
            dog_gender = request_data[api_key.DOG_GENDER]
        else:
            return f'{api_key.DOG_GENDER} was not found', 400

        if api_key.DOG_AGE in request_data:
            r_dog_age = request_data[api_key.DOG_AGE]
            l_ages = r_dog_age.split('-')
            dog_age = (int(l_ages[0]) * 12) + int(l_ages[1])
            print(f'dog age : {dog_age}')
        else:
            return f'{api_key.DOG_AGE} was not found', 400

        if api_key.BREED in request_data:
            raw_breed = request_data[api_key.BREED]
            breed = map_breed(raw_breed)
            if breed == 'error':
                return f'{raw_breed} does not support, please check spelling in Thai', 400
        else:
            return f'{api_key.BREED} was not found', 400

        if api_key.LOCATION in request_data:
            lat = request_data[api_key.LOCATION]['lat']
            long = request_data[api_key.LOCATION]['long']
            location= firestore.GeoPoint(lat, long)            
        else:
            return f'{api_key.LOCATION} was not found', 400

    # check if the customer exists 
    customer_doc = db.collection(firestore_collection.REGISTER).document(customer_id).get()
    if customer_doc.exists:
        print('customer has already existed')
    else:        
         db.collection(firestore_collection.REGISTER).document(customer_id).set({'display_name': display_name})
         print('register new customer')

    customer = {
        'customer_id': customer_id,
        'owner_name': owner_name,
        'phone': phone,
    }
    dog = {
        'name': dog_name,
        'breed': breed,
        'image': image,
        'age': dog_age,
        'gender': dog_gender,
        'location': location,
    }

    dogs = db.collection(firestore_collection.LOST).document(customer_id).collection(firestore_collection.LOST_DOGS).where('name', '==', dog_name).where('is_found', '==', False).get()
    print(f'dogs.length : {len(dogs)}')

    if len(dogs) > 0:
        return f'{dog_name} was already declared as lost', 200

    add_dog_to_lost(customer, dog)

    matchDf = scan_dogs(dog, firestore_collection.FOUND_DOGS)
    result = matchDf.to_dict('records')
    return json.dumps(result, indent=4), 200

@app.route('/found', methods = ['POST'])
def found_api():
    request_data = request.get_json()

    customer_id = None
    display_name = None
    image = None
    lat = None
    long = None
    location = None

    if request_data:
        if api_key.CUSTOMER_ID in request_data:
            customer_id = request_data[api_key.CUSTOMER_ID]
        else:
            return f'{api_key.CUSTOMER_ID} was not found', 400

        if api_key.DISPLAY_NAME in request_data:
            display_name = request_data[api_key.DISPLAY_NAME]

        if api_key.IMAGE in request_data:
            image = request_data[api_key.IMAGE]
        else:
            return f'{api_key.IMAGE} was not found', 400      

        if api_key.LOCATION in request_data:
            lat = request_data[api_key.LOCATION]['lat']
            long = request_data[api_key.LOCATION]['long']
            location= firestore.GeoPoint(lat, long)            
        else:
            return f'{api_key.LOCATION} was not found', 400

    breed = predict_breed(image)
    data = {}
    if display_name:
        data['display_name'] = display_name
    db.collection(firestore_collection.FOUND).document(customer_id).set(data)

    dog = {
        'breed': breed,
        'image': image,
        'location': location,
        'is_match': False,
        'datetime': datetime.now(),
    }
    db.collection(firestore_collection.FOUND).document(customer_id).collection(firestore_collection.FOUND_DOGS).add(dog)

    matchDf = scan_dogs(dog, firestore_collection.LOST_DOGS)
    result = matchDf.to_dict('records')
    return json.dumps(result, indent=4), 200

#TODO: PREM
def predict_breed(image):
    breeds = ['beagle', 'poodle', 'siberian husky', 'pug', 'pomeranian', 'shih tzu', 'chow chow', 'crogi', 'akita inu', 'bernard']
    index = random.randint(0, 9)
    return breeds[index]

# for debugging/testing code purpose
@app.route('/test', methods = ['POST'])
def test_api():
    request_data = request.get_json()
    
    image = None   
    breed = None
    lat = None
    long = None
    location = None
    case = None

    if request_data:
        if api_key.IMAGE in request_data:
            image = request_data[api_key.IMAGE]
        else:
            return f'{api_key.IMAGE} was not found', 400        

        if api_key.BREED in request_data:
            raw_breed = request_data[api_key.BREED]
            breed = map_breed(raw_breed)
            if breed == 'error':
                return f'{raw_breed} does not support, please check spelling', 400
        else:
            return f'{api_key.BREED} was not found', 400

        if api_key.LOCATION in request_data:
            lat = request_data[api_key.LOCATION]['lat']
            long = request_data[api_key.LOCATION]['long']
            location= firestore.GeoPoint(lat, long)            
        else:
            return f'{api_key.LOCATION} was not found', 400

        if 'case' in request_data:
            case = request_data['case']
        else:
            return f'case was not found', 400  

    dog = {
        'breed': breed,
        'image': image,
        'location': location,
    }
    collection_group = None
    if case == 'lost':
        collection_group = firestore_collection.LOST_DOGS
    elif case == 'found':
        collection_group = firestore_collection.FOUND_DOGS
    else:
        return f'test API does not support case : {case}, it MUST be either lost or found', 400

    matchDf = scan_dogs(dog, collection_group)
    result = matchDf.to_dict('records')
    return json.dumps(result, indent=4), 200

# TODO : PREM
# need to return top 5 dog that match the given dog parameter
def match_dogs(dog, df):
#    example dataframe
#          dog_id            breed             image            distance gender     age
# 0  I5uYoz6psULpitPvHb0z  chow chow  s3-image-url-from-botnoi  5.409976   0        18
# 1  0nLFAazd6Lht41i5bJVB  chow chow  s3-image-url-from-botnoi  2.251150   1        6
    return df

def scan_dogs(dog, collection_name):
    print(dog)
    breed = dog['breed']
    docs = db.collection_group(collection_name).where('breed', '==', breed).get()
    print(f'there are {len(docs)} {breed} dogs in system')
    location = dog['location']
    lat = location.latitude
    long = location.longitude
    source = (lat, long)
    dataset = []
    for doc in docs:        
        data = doc.to_dict()
        print(f'{doc.id} => {data}')
        destination = (data['location'].latitude, data['location'].longitude)
        dist = distance.distance(source, destination).km # get distance between 2 geo points
        print(f'distance between dogs is {dist} km.')

        if (dist < RADIUS):
            row = {
                'dog_id': doc.id,
                'breed': data['breed'],
                'image': data['image'],
                'distance': dist,
            }
            if 'name' in data:
                row['name'] = data['name']
            dataset.append(row)

    pd.set_option('display.width', 120)
    df = pd.DataFrame(dataset)
    print('printing data frame')
    print(df)
    matchDf = match_dogs(dog, df)
    return matchDf

def swap_dict(old_dict):
    new_dict = {}
    for key, value in old_dict.items():
        if value in new_dict:
            new_dict[value].append(key)
        else:
            new_dict[value] = key
    return new_dict

def map_breed(breed, reverse=False):
    breeds = {
        'ชิวาว่า': 'Chihuahua',
        'โกลเด้น': 'Golden Retriever',
        'บางแก้ว': 'Bangkaew',
        'ชิสุ': 'Shih-tzu',
        'ชิบะ': 'Shiba',
        'ไซบีเรียนฮัสกี้': 'Siberian Husky',
        'ปั๊ก': 'Pug',
        'คอร์กี้': 'Corgi',
        'เฟรนช์บูลด๊อก': 'French Bulldog',
        'ปอมเมอเรเนียน': 'Pomeranian',
        'ไทยหลังอาน': 'Thai Ridgeback',
        'ลาบราดอร์': 'Labrador Retriever',
        'พุดเดิ้ล': 'Poodle',
        'บีเกิ้ล': 'Beagle',
        'เยอรมันเชพเพิร์ด (อัลเซเชี่ยน)': 'German shepherd',
        'บูลด็อก': 'Bulldog',
        'แจ็กรัสเซลล์': 'Jack Russell Terrier',
        'บาสเซ็ตฮาวด์': 'Basset Hound',
        'มินิเอเจอร์พินเชอร์': 'Miniature Pinscher',
        'ชเนาเซอร์': 'Miniature Schnauzer',
    }
    if reverse:
        breeds = swap_dict(breeds)

    result = breeds.get(breed, 'error')
    return result

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)