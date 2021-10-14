import sys
import os
from flask import Flask, flash, request, render_template
from datetime import datetime
import pandas as pd
import pickle
import random
from decimal import Decimal
import json 
import math
import geopy
from geopy import distance

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import api_key
import firestore_collection

from linebot import (
    LineBotApi
)
from linebot.models import *

channel_access_token = 'Fyq3NWVJzqGnHAns06nRZN0vsPA9BMJcsr3OMsxMSv/anHdOD3UU0//4SONu5GIXYE6CuV+37vlAr59R8kjwgj+VuQyGGPKD7SymgOTaC2ShIhqwQ3TnJ+bFOZmy9t9/ukH4gZ35VSPaeDA8nyxH1AdB04t89/1O/w1cDnyilFU='

line_bot_api = LineBotApi(channel_access_token)

RADIUS = 5 ## unit is KM

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

app = Flask(__name__)

@app.route('/')
def home():
    print_heroku('API is running')
    return 'API is running'

@app.route('/register', methods = ['POST'])
def register_api():
    request_data = request.get_json()
    print_heroku('request JSON')
    print_heroku(request_data)

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
            return create_response('error', 400, f'{api_key.CUSTOMER_ID} was not found')

        if api_key.OWNER_NAME in request_data:
            owner_name = request_data[api_key.OWNER_NAME]
        else:
            return create_response('error', 400, f'{api_key.OWNER_NAME} was not found')

        if api_key.DOG_AGE in request_data:
            r_dog_age = request_data[api_key.DOG_AGE]
            l_ages = r_dog_age.split('-')
            dog_age = (int(l_ages[0]) * 12) + int(l_ages[1])
            print_heroku(f'dog age : {dog_age}')
        else:
            return create_response('error', 400, f'{api_key.DOG_AGE} was not found')

        if api_key.DOG_GENDER in request_data:
            dog_gender = request_data[api_key.DOG_GENDER]
        else:
            return create_response('error', 400, f'{api_key.DOG_GENDER} was not found')

        if api_key.DISPLAY_NAME in request_data:
            display_name = request_data[api_key.DISPLAY_NAME]

        if api_key.IMAGE in request_data:
            image = request_data[api_key.IMAGE]
        else:
            return create_response('error', 400, f'{api_key.IMAGE} was not found')

        if api_key.DOG in request_data:
            dog_name = request_data[api_key.DOG].lower()
        else:
            return create_response('error', 400, f'{api_key.api_key} was not found')

        if api_key.BREED in request_data:            
            raw_breed = request_data[api_key.BREED]
            breed = map_breed(raw_breed)
            if breed == 'error':
                return create_response('error', 400, f'{raw_breed} does not support, please check spelling')

            print_heroku(f'English breed : {breed}')
            thai_breed = map_breed(breed, True)
            print_heroku(f'Thai breed : {thai_breed}')
            type_breed = type(thai_breed)
            print_heroku(f'type of thai breed : {type_breed}')
        else:
            return create_response('error', 400, f'{api_key.BREED} was not found')
        
    customer = {
        'display_name': display_name,
        'owner_name': owner_name,
    }
    print_heroku(request_data)
    db.collection(firestore_collection.REGISTER).document(customer_id).set(customer) ## add or update the user profile   
    dogs = db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).where('name', '==', dog_name).get()
    print_heroku(f'dogs.length : {len(dogs)}')

    if len(dogs) > 0:
        return create_response('ok', 200, f'{dog_name} was already register')

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
   
    return create_response('ok', 200, f'Successfully register {dog_name} to our system')
    # return {'status': 'OK', 'message': f'Successfully register {dog_name} to our system'}, 200

def create_response(status, code, message):
    return {'status': status, 'message': message}, code

@app.route('/get-registered')
def get_registered_user_api():
    customer_id = request.args.get('customer_id') 
    customer = db.collection(firestore_collection.REGISTER).document(customer_id).get()
    intent_name = 'int_Register_Not_Found'
    message = None
    if customer.exists:
        intent_name = 'int_Register_Found'

    if intent_name == 'int_Register_Found':
        message = f'customer id : {customer_id} has been registered'
    else:
        message = f'customer id : {customer_id} has NOT registered yet'

    output = {
        'intent_name': intent_name,
        'message': message,
        'status': 'ok',
    }
    return output, 200

@app.route('/get-dogs')
def get_dogs_api():
    customer_id = request.args.get('customer_id')
    customer = db.collection(firestore_collection.REGISTER).document(customer_id).get()
    if not customer.exists:
        return create_response('error', 404, f'customer_id : {customer_id} was not exists')

    print_heroku(f'customer_id : {customer_id}')
    docs = db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).stream() # get alled', '==', False).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()        
        print_heroku(f'{doc.id} => {data}')
        results.append({
            "dog_id": doc.id,
            "name": data['name'],
            "breed": map_breed(data['breed'], True),
            "image": data['image'],
            "dog_age": data['age'],
            "dog_gender": data['gender'],
        })
    
    flex_json = create_flex(results)
    notify_flex(customer_id, 'รายการน้องหมาที่ลงทะเบียน', flex_json)
    print_heroku(flex_json)
    return create_response('ok', '200', f'successfully push registered dog list to customer : {customer_id}')

# http://localhost:5000/get-flex-dog-info?customer_id=Ufc5c40adb25791d5da4e25012b6023f8&dog_id=WJF5KdDRgjaBLVQHSF8M&phone=0847485152&address=หมู่บ้านการบินไทย 77/99&latitude=13.912512763412861&longitude=100.55167378245899&reward=5000 บาท&note=ไม่มี
# https://dog-finder01.herokuapp.com/get-flex-dog-info?customer_id={customer_id}&dog_id={dog_id}&=phone={phone}&address={address}&latitude={latitude}&longitude={longitude}&reward={reward}&note={note}
@app.route('/get-flex-dog-info')
def get_flex_dog_info_api():
    customer_id = request.args.get('customer_id')
    if not customer_id:
        return create_response('error', 400, 'customer_id was not found')

    dog_id = request.args.get('dog_id')
    if not dog_id:
        return create_response('error', 400, 'dog_id was not found')

    phone = request.args.get('phone')
    if not phone:
        return create_response('error', 400, 'phone was not found')

    reward = request.args.get('reward')
    if not reward:
        reward = 'ไม่มี'

    address = request.args.get('address')
    if not address:
        return create_response('error', 400, 'address was not found')

    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')
    lat = Decimal(latitude)
    long = Decimal(longitude)
    location= firestore.GeoPoint(lat, long)
    note = request.args.get('note')
    if not note:
        note = 'ไม่มี'

    customer_doc = db.collection(firestore_collection.REGISTER).document(customer_id).get()
    if not customer_doc.exists:
        return create_response('error', 404, f'customer_id : {customer_id} was not exists')

    dog_doc = db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).document(dog_id).get()
    if not dog_doc.exists:
        return create_response('error', 404, f'dog_id : {dog_id} was not found')

    customer = customer_doc.to_dict()
    customer['phone'] = phone
    dog = dog_doc.to_dict()
    dog['location'] = location
    dog['address'] = address
    dog['note'] = note
    dog['reward'] = reward
    print_heroku('customer info')
    print_heroku(customer)
    print_heroku('dog info')
    print_heroku(dog)
    flex_json = create_flex_confirm_dog_test(customer, dog)
    print_heroku(flex_json)
    notify_flex(customer_id, 'โปรดยืนยันการแจ้งหาย', flex_json)
    return create_response('ok', 200, 'successfully push get flex dog info')

def create_flex_confirm_dog_test(customer, dog):
    image = dog['image']
    dog_name = dog['name']
    breed = dog['breed']
    address = dog['address']
    reward = dog['reward']
    note = dog['note']
    phone = customer['phone']
    owner_name = customer['owner_name']
    dog_age = convert_month_to_year_month_in_thai(dog['age'])
    dog_gender = dog['gender']
    print_heroku(f'dog_age : {dog_age}')

    flex = {
        "type": "bubble",
        "header": {
            "backgroundColor": "#525B35",
            "contents": [
            {
                "align": "start",
                "flex": 1,
                "gravity": "center",
                "size": "lg",
                "type": "image",
                "url": "https://www.img.in.th/images/fa483e18975191b2aee90efdc4e89413.png"
            },
            {
                "contents": [
                {
                    "type": "filler"
                },
                {
                    "align": "center",
                    "color": "#FFFFFF",
                    "gravity": "center",
                    "size": "xl",
                    "text": dog_name,
                    "type": "text",
                    "weight": "bold",
                    "wrap": True
                },
                {
                    "type": "filler"
                }
                ],
                "flex": 2,
                "layout": "vertical",
                "type": "box"
            }
            ],
            "layout": "horizontal",
            "type": "box"
        },
        "body": {
            "contents": [
            {
                "contents": [
                {
                    "aspectMode": "cover",
                    "size": "full",
                    "type": "image",
                    "url": image,
                },
                {
                    "margin": "xl",
                    "type": "separator"
                }
                ],
                "cornerRadius": "sm",
                "layout": "vertical",
                "type": "box"
            },
            {
                "contents": [
                {
                    "contents": [
                    {
                        "flex": 3,
                        "size": "sm",
                        "text": "ชื่อ:",
                        "type": "text"
                    },
                    {
                        "flex": 12,
                        "size": "sm",
                        "text": dog_name,
                        "type": "text",
                        "weight": "bold"
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "contents": [
                    {
                        "flex": 3,
                        "size": "sm",
                        "text": "พันธุ์:",
                        "type": "text"
                    },
                    {
                        "flex": 12,
                        "size": "sm",
                        "text": breed,
                        "type": "text",
                        "weight": "bold"
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "contents": [
                    {
                        "flex": 6,
                        "size": "sm",
                        "text": "อายุ (ปี-เดือน):",
                        "type": "text"
                    },
                    {
                        "align": "start",
                        "flex": 8,
                        "size": "sm",
                        "text": dog_age,
                        "type": "text",
                        "weight": "bold"
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "contents": [
                    {
                        "flex": 2,
                        "size": "sm",
                        "text": "เพศ:",
                        "type": "text"
                    },
                    {
                        "align": "start",
                        "flex": 12,
                        "size": "sm",
                        "text": dog_gender,
                        "type": "text",
                        "weight": "bold"
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                }
                ],
                "layout": "vertical",
                "type": "box"
            },
            {
                "margin": "xxl",
                "type": "separator"
            },
            {
                "contents": [
                {
                    "contents": [
                    {
                        "align": "start",
                        "flex": 3,
                        "size": "sm",
                        "text": "เจ้าของ:",
                        "type": "text"
                    },
                    {
                        "flex": 10,
                        "size": "sm",
                        "text": owner_name,
                        "type": "text",
                        "weight": "bold",
                        "wrap": True
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "contents": [
                    {
                        "flex": 3,
                        "size": "sm",
                        "text": "เบอร์ติดต่อ:",
                        "type": "text"
                    },
                    {
                        "flex": 6,
                        "size": "sm",
                        "text": phone,
                        "type": "text",
                        "weight": "bold"
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "contents": [
                    {
                        "align": "start",
                        "flex": 3,
                        "size": "sm",
                        "text": "รางวัล:",
                        "type": "text"
                    },
                    {
                        "flex": 12,
                        "size": "sm",
                        "text": reward,
                        "type": "text",
                        "weight": "bold",
                        "wrap": True
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "margin": "lg",
                    "type": "separator"
                },
                {
                    "contents": [
                    {
                        "align": "center",
                        "flex": 3,
                        "size": "sm",
                        "text": "หายที่:",
                        "type": "text"
                    },
                    {
                        "size": "sm",
                        "text": address,
                        "type": "text",
                        "wrap": True
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "center",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "vertical",
                    "margin": "lg",
                    "type": "box"
                },
                {
                    "type": "separator"
                },
                {
                    "contents": [
                    {
                        "align": "center",
                        "flex": 3,
                        "size": "sm",
                        "text": "ข้อความ:",
                        "type": "text"
                    },
                    {
                        "size": "sm",
                        "text": note,
                        "type": "text",
                        "wrap": True
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "center",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "vertical",
                    "margin": "lg",
                    "type": "box"
                }
                ],
                "layout": "vertical",
                "margin": "lg",
                "type": "box"
            }
            ],
            "layout": "vertical",
            "type": "box"
        },
        "footer": {
            "contents": [
            {
                "align": "center",
                "color": "#FF0000",
                "size": "xs",
                "text": "ถ้าข้อมูลถูกต้องและต้องการแจ้งหาย กดปุ่มยืนยันแจ้งหาย",
                "type": "text",
                "weight": "bold",
                "wrap": True
            },
            {
                "action": {
                "label": "ยืนยันแจ้งหาย",
                "text": "ยืนยันแจ้งหาย",
                "type": "message"
                },
                "color": "#525B35",
                "style": "primary",
                "type": "button"
            },
            {
                "margin": "md",
                "type": "separator"
            },
            {
                "action": {
                "label": "ยกเลิกการแจ้ง",
                "text": "ยกเลิกการแจ้ง",
                "type": "message"
                },
                "color": "#525B35",
                "style": "primary",
                "type": "button"
            }
            ],
            "layout": "vertical",
            "type": "box"
        }
    }
    return flex

def create_flex_confirm_dog(customer, dog):
    image = dog['image']
    dog_name = dog['name']
    breed = dog['breed']
    address = dog['address']
    reward = dog['reward']
    note = dog['note']
    phone = customer['phone']
    owner_name = customer['owner_name']
    dog_age = convert_month_to_year_month_in_thai(dog['age'])
    dog_gender = dog['gender']

    flex = {
        "type": "bubble",
        "header": {
            "backgroundColor": "#525B35",
            "contents": [
            {
                "align": "start",
                "flex": 1,
                "gravity": "center",
                "size": "lg",
                "type": "image",
                "url": "https://www.img.in.th/images/fa483e18975191b2aee90efdc4e89413.png"
            },
            {
                "contents": [
                {
                    "type": "filler"
                },
                {
                    "align": "center",
                    "color": "#FFFFFF",
                    "gravity": "center",
                    "size": "xl",
                    "text": f"{dog_name}",
                    "type": "text",
                    "weight": "bold",
                    "wrap": True
                },
                {
                    "type": "filler"
                }
                ],
                "flex": 2,
                "layout": "vertical",
                "type": "box"
            }
            ],
            "layout": "horizontal",
            "type": "box"
        },
        "body": {
            "contents": [
            {
                "contents": [
                {
                    "aspectMode": "cover",
                    "size": "full",
                    "type": "image",
                    "url": f"{image}"
                },
                {
                    "margin": "xl",
                    "type": "separator"
                }
                ],
                "cornerRadius": "sm",
                "layout": "vertical",
                "type": "box"
            },
            {
                "contents": [
                {
                    "contents": [
                    {
                        "flex": 3,
                        "size": "sm",
                        "text": "ชื่อ:",
                        "type": "text"
                    },
                    {
                        "flex": 12,
                        "size": "sm",
                        "text": f"{dog_name}",
                        "type": "text",
                        "weight": "bold"
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "contents": [
                    {
                        "flex": 3,
                        "size": "sm",
                        "text": "พันธุ์:",
                        "type": "text"
                    },
                    {
                        "flex": 12,
                        "size": "sm",
                        "text": f"{breed}",
                        "type": "text",
                        "weight": "bold"
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "contents": [
                    {
                        "flex": 6,
                        "size": "sm",
                        "text": "อายุ (ปี-เดือน):",
                        "type": "text"
                    },
                    {
                        "align": "start",
                        "flex": 8,
                        "size": "sm",
                        "text": f"{dog_age}",
                        "type": "text",
                        "weight": "bold"
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "contents": [
                    {
                        "flex": 2,
                        "size": "sm",
                        "text": "เพศ:",
                        "type": "text"
                    },
                    {
                        "align": "start",
                        "flex": 12,
                        "size": "sm",
                        "text": f"{dog_gender}",
                        "type": "text",
                        "weight": "bold"
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                }
                ],
                "layout": "vertical",
                "type": "box"
            },
            {
                "margin": "xxl",
                "type": "separator"
            },
            {
                "contents": [
                {
                    "contents": [
                    {
                        "align": "start",
                        "flex": 3,
                        "size": "sm",
                        "text": "เจ้าของ:",
                        "type": "text"
                    },
                    {
                        "flex": 10,
                        "size": "sm",
                        "text": f"{owner_name}",
                        "type": "text",
                        "weight": "bold",
                        "wrap": True
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "contents": [
                    {
                        "flex": 3,
                        "size": "sm",
                        "text": "เบอร์ติดต่อ:",
                        "type": "text"
                    },
                    {
                        "flex": 6,
                        "size": "sm",
                        "text": f"{phone}",
                        "type": "text",
                        "weight": "bold"
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "contents": [
                    {
                        "align": "start",
                        "flex": 3,
                        "size": "sm",
                        "text": "รางวัล:",
                        "type": "text"
                    },
                    {
                        "flex": 12,
                        "size": "sm",
                        "text": f"{reward}",
                        "type": "text",
                        "weight": "bold",
                        "wrap": True
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "end",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "horizontal",
                    "type": "box"
                },
                {
                    "margin": "lg",
                    "type": "separator"
                },
                {
                    "contents": [
                    {
                        "align": "center",
                        "flex": 3,
                        "size": "sm",
                        "text": "หายที่:",
                        "type": "text"
                    },
                    {
                        "size": "sm",
                        "text": f"{address}",
                        "type": "text",
                        "wrap": True
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "center",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "vertical",
                    "margin": "lg",
                    "type": "box"
                },
                {
                    "type": "separator"
                },
                {
                    "contents": [
                    {
                        "align": "center",
                        "flex": 3,
                        "size": "sm",
                        "text": "ข้อความ:",
                        "type": "text"
                    },
                    {
                        "size": "sm",
                        "text": f"{note}",
                        "type": "text",
                        "wrap": True
                    },
                    {
                        "action": {
                        "label": "กำลังทำ function นี้",
                        "text": "กำลังทำ function นี้",
                        "type": "message"
                        },
                        "align": "center",
                        "flex": 2,
                        "size": "xs",
                        "text": "แก้ไข",
                        "type": "text"
                    }
                    ],
                    "layout": "vertical",
                    "margin": "lg",
                    "type": "box"
                }
                ],
                "layout": "vertical",
                "margin": "lg",
                "type": "box"
            }
            ],
            "layout": "vertical",
            "type": "box"
        },
        "footer": {
            "contents": [
            {
                "align": "center",
                "color": "#FF0000",
                "size": "xs",
                "text": "ถ้าข้อมูลถูกต้องและต้องการแจ้งหาย กดปุ่มยืนยันแจ้งหาย",
                "type": "text",
                "weight": "bold",
                "wrap": True
            },
            {
                "action": {
                "label": "ยืนยันแจ้งหาย",
                "text": "ยืนยันแจ้งหาย",
                "type": "message"
                },
                "color": "#525B35",
                "style": "primary",
                "type": "button"
            },
            {
                "margin": "md",
                "type": "separator"
            },
            {
                "action": {
                "label": "ยกเลิกการแจ้ง",
                "text": "ยกเลิกการแจ้ง",
                "type": "message"
                },
                "color": "#525B35",
                "style": "primary",
                "type": "button"
            }
            ],
            "layout": "vertical",
            "type": "box"
        }
    }
    return flex

def create_flex(dogs):
    flex = {
        'type': 'carousel',
    }
    contents = []
    i = 1
    for dog in dogs:
         content = {
             'body': {
                'contents': [
                    {
                        'contents': [],
                        'size': 'xl',
                        'text': dog['name'],
                        'type': 'text',
                        'weight': 'bold',
                        'wrap': True,
                    }
                ],
                'layout': 'vertical',
                'spacing': 'sm',
                'type': 'box',
             },
             'footer': {
                 'contents': [
                     {
                         'action': {
                             'type': 'message',
                             'label': 'แจ้งหาย',
                             'text': dog['dog_id'],
                         },
                         'style': 'primary',
                         'type': 'button',
                     }
                 ],
                'layout': 'vertical',
                'spacing': 'sm',
                'type': 'box',
             },
             'hero': {
                'aspectMode': 'fit',
                'aspectRatio': '20:13',
                'size': 'full',
                'type': 'image',
                'url': dog['image'],
             },
             'type': 'bubble',
         }
         i = i + 1
         contents.append(content)    

    flex['contents'] = contents
    return flex

def create_flex_found_dog(dogs):
    flex = {
        'type': 'carousel',
    }
    contents = []
    i = 1
    for dog in dogs:
         content = {
             'body': {
                'contents': [                
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                    {
                        "type": "text",
                        "text": "โปรดติดต่อผู้พบเห็นตามเบอร์ที่ให้ไว้",
                        "color": "#FF0000",
                        "align": "center",
                        "size": "sm"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                        {
                            "type": "text",
                            "text": "ผู้พบ:",
                            "flex": 3,
                            "size": "sm",
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": dog['founder'],
                            "flex": 15,
                            "size": "sm",
                            "weight": "bold"
                        }
                        ],
                        "margin": "sm"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                        {
                            "type": "text",
                            "text": "เบอร์ติดต่อ:",
                            "flex": 6,
                            "size": "sm",
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": dog['phone'],
                            "flex": 14,
                            "size": "sm",
                            "weight": "bold"
                        }
                        ]
                    }
                    ],
                    "margin": "lg"
                }
                ],
                'layout': 'vertical',
                'spacing': 'sm',
                'type': 'box',
             },
             'footer': {
                'contents': [],
                'layout': 'vertical',
                'spacing': 'sm',
                'type': 'box',
             },
             'hero': {
                'aspectMode': 'fit',
                'aspectRatio': '20:13',
                'size': 'full',
                'type': 'image',
                'url': dog['image'],
             },
             'type': 'bubble',
         }
         i = i + 1
         contents.append(content)    

    flex['contents'] = contents
    return flex

def create_flex_lost_dog(dogs, founder):
    flex = {
        'type': 'carousel',
    }
    contents = []
    i = 1
    for dog in dogs:
         content = {
             'body': {
                'contents': [
                {
                    "type": "text",
                    "text": dog['name'],
                    "wrap": True,
                    "weight": "bold",
                    "size": "xl"
                },
                {
                    "type": "separator"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                    {
                        "type": "text",
                        "text": "โปรดติดต่อผู้พบเห็นตามเบอร์ที่ให้ไว้",
                        "color": "#FF0000",
                        "align": "center",
                        "size": "sm"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                        {
                            "type": "text",
                            "text": "ผู้พบ:",
                            "flex": 3,
                            "size": "sm",
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": founder['name'],
                            "flex": 15,
                            "size": "sm",
                            "weight": "bold"
                        }
                        ],
                        "margin": "sm"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                        {
                            "type": "text",
                            "text": "เบอร์ติดต่อ:",
                            "flex": 6,
                            "size": "sm",
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": founder['phone'],
                            "flex": 14,
                            "size": "sm",
                            "weight": "bold"
                        }
                        ]
                    }
                    ],
                    "margin": "lg"
                }
                ],
                'layout': 'vertical',
                'spacing': 'sm',
                'type': 'box',
             },
             'footer': {
                'contents': [],
                'layout': 'vertical',
                'spacing': 'sm',
                'type': 'box',
             },
             'hero': {
                'aspectMode': 'fit',
                'aspectRatio': '20:13',
                'size': 'full',
                'type': 'image',
                'url': founder['image'],
             },
             'type': 'bubble',
         }
         i = i + 1
         contents.append(content)    

    flex['contents'] = contents
    return flex

def notify_flex(customer_id, alt_message, flex_json):
    line_bot_api.push_message(customer_id, FlexSendMessage(alt_text=alt_message, contents=flex_json))

# customer_id is the dog owner
# dog is the lost dog
# founder will contains name and phone
def notify_found_dog(customer_id, dog, founder):
    founder_name = founder['name']
    phone = founder['phone']
    flex_json = create_flex_lost_dog([dog], founder)
    # line_bot_api.push_message(customer_id, TextSendMessage(text=f'founder name : {founder_name} , phone : {phone}'))
    notify_flex(customer_id, 'พบน้องหมาลักษณะใกล้เคียง', flex_json)

def add_dog_to_lost(customer, dog):
    customer_id = customer['customer_id']
    owner_doc = db.collection(firestore_collection.REGISTER).document(customer_id)
    db.collection(firestore_collection.LOST).document(customer_id).set({
        'datetime': datetime.now(),
    })

    saved_lost_customer = db.collection(firestore_collection.LOST).document(customer_id).get()
    if not saved_lost_customer.exists:
        print_heroku(f'count not find {customer_id} in lost collection')

    dog_json = {
        'name': dog['name'],
        'breed': dog['breed'],
        'image': dog['image'],
        'location': dog['location'],
        'age': dog['age'],
        'gender': dog['gender'],
        'is_found': False,
        'datetime': datetime.now(),
        'owner': owner_doc,
    }

    dog_id = None
    if 'dog_id' in dog:
        dog_id = dog['dog_id']
        print(f'setting dog from existing dog_id : {dog_id}')
        db.collection(firestore_collection.LOST).document(customer_id).collection(firestore_collection.LOST_DOGS).document(dog_id).set(dog_json)
    else:    
        db.collection(firestore_collection.LOST).document(customer_id).collection(firestore_collection.LOST_DOGS).add(dog_json)
    # remove customer id as we don't need this field
    del customer['customer_id']
    # update customer info
    owner_doc.update(customer)

    if 'dog_id' in dog:
        dog_id = dog['dog_id']
    else:
        result_doc = db.collection(firestore_collection.LOST).document(customer_id).collection(firestore_collection.LOST_DOGS).where('name', '==', dog['name']).get()[0]
        print_heroku(f'result_doc.exists : {result_doc.exists}')
        # db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).where('is_informed', '==', False).stream()
        dog_id = result_doc.id

    print_heroku(f'saved dog_id : {dog_id}')
    return dog_id

@app.route('/lost-preregister', methods = ['POST'])
def lostpreregister_api():
    request_data = request.get_json()
    print_heroku('JSON')
    print_heroku(request_data)
    customer_id = None
    phone = None
    dog_id = None
    location = None
    address = None
    lat = None
    long = None
    reward = None
    note = None
    

    if request_data:
        if api_key.CUSTOMER_ID in request_data:
            customer_id = request_data[api_key.CUSTOMER_ID]
        else:
            return create_response('error', 400, f'{api_key.CUSTOMER_ID} was not found')
        
        if api_key.PHONE in request_data:
            phone = request_data[api_key.PHONE]
        else:
            return create_response('error', 400, f'{api_key.PHONE} was not found')

        if api_key.LOCATION in request_data:
            lat = Decimal(request_data[api_key.LOCATION][api_key.LAT])
            long = Decimal(request_data[api_key.LOCATION][api_key.LONG])
            address = request_data[api_key.LOCATION][api_key.ADDRESS]
            location= firestore.GeoPoint(lat, long)
        else:
            return create_response('error', 400, f'{api_key.LOCATION} was not found')

        if api_key.DOG_ID in request_data:
            dog_id = request_data[api_key.DOG_ID]
        else:
            return create_response('error', 400, f'{api_key.DOG_ID} was not found')

        if api_key.REWARD in request_data:
            reward = request_data[api_key.REWARD]
        else:
            return create_response('error', 400, f'{api_key.REWARD} was not found')

        if api_key.NOTE in request_data:
            note = request_data[api_key.NOTE]
        else:
            return create_response('error', 400, f'{api_key.NOTE} was not found')

    # get dog from register collection
    doc = db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).document(dog_id).get()
    if not doc.exists:
        return create_response('error', 404, f'dog_id {dog_id} was not found')

    print_heroku(doc.to_dict())

    dog = doc.to_dict()    
    dog_name = dog['name']
    dogs = db.collection(firestore_collection.LOST).document(customer_id).collection(firestore_collection.LOST_DOGS).where('name', '==', dog_name).where('is_found', '==', False).get()
    print_heroku(f'dogs.length : {len(dogs)}')

    if len(dogs) > 0:
        return create_response('ok', 200, f'{dog_name} was already declared as lost')
    
    dog['dog_id'] = dog_id
    dog['location'] = location
    dog['address'] = address
    dog['reward'] = reward
    dog['note'] = note
    customer = {
        'customer_id': customer_id,
        'phone': phone,
    }
    add_dog_to_lost(customer, dog)

    matchDf = scan_found_dogs(dog)
    intent_name = 'int_Lost_Preregister_Not_Found'
    match_rows = matchDf.shape[0] # count dataframe records
    if match_rows > 0:
        intent_name = 'int_Lost_Preregister_Found'
    
    message = f'there are {match_rows} dogs match with your dog {dog_name}'

    return {
        'dog_id': dog_id,
        'intent_name': intent_name,
        'message': message,
        'status': 'ok',
    }

## for the case we don't do the pre-register before
@app.route('/lost-register', methods = ['POST'])
def lost_api():
    request_data = request.get_json()
    print_heroku('JSON')
    print_heroku(request_data)
    customer_id = None
    display_name = None
    owner_name = None
    phone = None
    image = None
    dog_name = None
    dog_gender = None
    dog_age = None
    breed = None
    location = None
    address = None
    lat = None
    long = None
    reward = None
    note = None
    

    if request_data:
        if api_key.CUSTOMER_ID in request_data:
            customer_id = request_data[api_key.CUSTOMER_ID]
        else:
            return create_response('error', 400, f'{api_key.CUSTOMER_ID} was not found')

        if api_key.OWNER_NAME in request_data:
            owner_name = request_data[api_key.OWNER_NAME]
        else:
            return create_response('error', 400, f'{api_key.OWNER_NAME} was not found')

        if api_key.PHONE in request_data:
            phone = request_data[api_key.PHONE]
        else:
            return create_response('error', 400, f'{api_key.PHONE} was not found')

        if api_key.DISPLAY_NAME in request_data:
            display_name = request_data[api_key.DISPLAY_NAME]

        if api_key.IMAGE in request_data:
            image = request_data[api_key.IMAGE]
        else:
            return create_response('error', 400, f'{api_key.IMAGE} was not found')

        if api_key.DOG in request_data:
            dog_name = request_data[api_key.DOG].lower()
        else:
            return create_response('error', 400, f'{api_key.DOG} was not found')

        if api_key.DOG_GENDER in request_data:
            dog_gender = request_data[api_key.DOG_GENDER]
        else:
            return create_response('error', 400, f'{api_key.DOG_GENDER} was not found')

        if api_key.DOG_AGE in request_data:
            r_dog_age = request_data[api_key.DOG_AGE]
            l_ages = r_dog_age.split('-')
            dog_age = (int(l_ages[0]) * 12) + int(l_ages[1])
            print_heroku(f'dog age : {dog_age}')
        else:
            return create_response('error', 400, f'{api_key.DOG_AGE} was not found')

        if api_key.BREED in request_data:
            raw_breed = request_data[api_key.BREED]
            breed = map_breed(raw_breed)
            if breed == 'error':
                return create_response('error', 400, f'{raw_breed} does not support, please check spelling in Thai')
        else:
            return create_response('error', 400, f'{api_key.BREED} was not found')

        if api_key.LOCATION in request_data:
            lat = Decimal(request_data[api_key.LOCATION][api_key.LAT])
            long = Decimal(request_data[api_key.LOCATION][api_key.LONG])
            address = request_data[api_key.LOCATION][api_key.ADDRESS]
            location= firestore.GeoPoint(lat, long)            
        else:
            return create_response('error', 400, f'{api_key.LOCATION} was not found')

        if api_key.REWARD in request_data:
            reward = request_data[api_key.REWARD]
        else:
            return create_response('error', 400, f'{api_key.REWARD} was not found')

        if api_key.NOTE in request_data:
            note = request_data[api_key.NOTE]
        else:
            return create_response('error', 400, f'{api_key.NOTE} was not found')

    # check if the customer exists 
    customer_doc = db.collection(firestore_collection.REGISTER).document(customer_id).get()
    if customer_doc.exists:
        print_heroku('customer has already existed')
    else:        
         db.collection(firestore_collection.REGISTER).document(customer_id).set({'display_name': display_name})
         print_heroku('register new customer')

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
        'address': address,
        'reward': reward,
        'note': note,
    }

    dogs = db.collection(firestore_collection.LOST).document(customer_id).collection(firestore_collection.LOST_DOGS).where('name', '==', dog_name).where('is_found', '==', False).get()
    print_heroku(f'dogs.length : {len(dogs)}')

    if len(dogs) > 0:
        return create_response('ok', 200, f'{dog_name} was already declared as lost')

    dog_id = add_dog_to_lost(customer, dog)

    matchDf = scan_found_dogs(dog)
    intent_name = 'int_Lost_Register_Not_Found'
    match_rows = matchDf.shape[0] # count dataframe records
    if match_rows > 0:
        intent_name = 'int_Lost_Register_Found'
    
    message = f'there are {match_rows} dogs match with your dog name : {dog_name}'

    return {      
        'dog_id': dog_id,  
        'intent_name': intent_name,
        'message': message,
        'status': 'ok',
    }

# https://dog-finder01.herokuapp.com/get-dog-info?customer_id={customer_id}&dog_id={dog_id}
@app.route('/get-dog-info')
def get_dog_info():
    customer_id = request.args.get('customer_id')
    dog_id = request.args.get('dog_id')
    print_heroku(f'customer_id : {customer_id}')
    print_heroku(f'dog_id : {dog_id}')

    customer_doc = db.collection(firestore_collection.REGISTER).document(customer_id).get()    
    if not customer_doc.exists:
        return create_response('error', 404, f'customer_id : {customer_id} was not found')

    customer = customer_doc.to_dict()
    print(customer)

    dog_doc = db.collection(firestore_collection.REGISTER).document(customer_id).collection(firestore_collection.REGISTERD_DOGS).document(dog_id).get()
    if not dog_doc.exists:
        return create_response('error', 404, f'dog_id : {dog_id} was not found')

    dog = dog_doc.to_dict()    
    dog_age = convert_month_to_year_month_in_thai(dog['age'])
    print_heroku(f'dog_age : {dog_age}')

    output_json = {
        'owner_name': customer['owner_name'],
        'image': dog['image'],
        'dog_name': dog['name'],
        'dog_gender': dog['gender'],
        'dog_age': dog_age,
        'breed': dog['breed'],
    }
    return output_json, 200

def convert_month_to_year_month_in_thai(month):
    if (month < 12):
        return f'{month} เดือน'

    if month % 12 == 0:
        year = math.trunc(month / 12)
        return f'{year} ปี'
    else:        
        year = math.trunc(month / 12)
        n_month = month % 12
        return f'{year} ปี {n_month} เดือน'
    

# https://dog-finder01.herokuapp.com/get-found-dogs?customer_id={customer_id}&dog_id={dog_id}
@app.route('/get-found-dogs')
def get_found_dogs_api():
    customer_id = request.args.get('customer_id')
    dog_id = request.args.get('dog_id')

    print_heroku(f'customer_id : {customer_id}')
    print_heroku(f'dog_id : {dog_id}')

    customer_doc = db.collection(firestore_collection.LOST).document(customer_id).get()
    print(customer_doc.to_dict())
    if not customer_doc.exists:
        return create_response('error', 404, f'customer_id : {customer_id} was not found')

    dog_doc = db.collection(firestore_collection.LOST).document(customer_id).collection(firestore_collection.LOST_DOGS).document(dog_id).get()
    if not dog_doc.exists:
        return create_response('error', 404, f'dog_id : {dog_id} was not found')

    lost_dog = dog_doc.to_dict()
    dog_name = lost_dog['name']
    matchDf = scan_found_dogs(lost_dog)
    # TODO : PREM get only match records
    # matchDf = match_dogs(dog_doc.to_dict(), matchDf)
    records = matchDf.to_dict('records')
    print_heroku(records)
    flex = create_flex_found_dog(records)
    print_heroku(flex)
    notify_flex(customer_id, f'รายการน้องหมาที่ใกล้เคียงกับ{dog_name}', flex)
    return create_response('ok', 200, f'successfully push list of found dogs to custoomer : {customer_id}')

@app.route('/predict-breed', methods = ['POST'])
def predict_breed_api():
    request_data = request.get_json()
    print_heroku('request JSON')
    image = None
    if request_data:
        # this is for testing, we can remove after integrate with Prem code in order to label breed
        if 'image' in request_data:
            input_breed = request_data['image']
        else:
            return create_response('error', 400, f'image was not found')

    breed = predict_breed(image)
    return {'status': 'ok', 'breed': breed}, 200

@app.route('/found', methods = ['POST'])
def found_api():
    request_data = request.get_json()
    print_heroku('request JSON')
    print_heroku(request_data)
    customer_id = None
    display_name = None
    founder_name = None
    image = None
    location = None
    address = None
    lat = None
    long = None
    phone = None
    note = None
    input_breed = None    

    if request_data:
        # this is for testing, we can remove after integrate with Prem code in order to label breed
        if api_key.BREED in request_data:
            input_breed = request_data[api_key.BREED]

        if api_key.CUSTOMER_ID in request_data:
            customer_id = request_data[api_key.CUSTOMER_ID]
        else:
            return create_response('error', 400, f'{api_key.CUSTOMER_ID} was not found')

        if api_key.FOUNDER_NAME in request_data:
            founder_name = request_data[api_key.FOUNDER_NAME]
        else:
            return create_response('error', 400, f'{api_key.FOUNDER_NAME} was not found')

        if api_key.DISPLAY_NAME in request_data:
            display_name = request_data[api_key.DISPLAY_NAME]

        if api_key.IMAGE in request_data:
            image = request_data[api_key.IMAGE]
        else:
            return create_response('error', 400, f'{api_key.IMAGE} was not found')

        if api_key.PHONE in request_data:
            phone = request_data[api_key.PHONE]
        else:
            return create_response('error', 400, f'{api_key.PHONE} was not found')

        if api_key.NOTE in request_data:
            note = request_data[api_key.NOTE]
        else:
            return create_response('error', 400, f'{api_key.NOTE} was not found')

        if api_key.LOCATION in request_data:
            lat = Decimal(request_data[api_key.LOCATION][api_key.LAT])
            long = Decimal(request_data[api_key.LOCATION][api_key.LONG])
            address = request_data[api_key.LOCATION][api_key.ADDRESS]
            location= firestore.GeoPoint(lat, long)            
        else:
            return create_response('error', 400, f'{api_key.LOCATION} was not found')

    breed = predict_breed(image)
    if input_breed:
        breed = input_breed # for testing only

    data = {
        'founder_name': founder_name,
        'phone': phone,
    }
    if display_name:
        data['display_name'] = display_name
    db.collection(firestore_collection.FOUND).document(customer_id).set(data)

    dog = {
        'breed': breed,
        'image': image,
        'location': location,
        'address': address,
        'is_match': False,
        'datetime': datetime.now(),
        'note': note,
    }
    db.collection(firestore_collection.FOUND).document(customer_id).collection(firestore_collection.FOUND_DOGS).add(dog)

    matchDf = scan_lost_dogs(dog)
    records = matchDf.to_dict('records')
    # test send notification

    founder = {
        'name': founder_name,
        'phone': phone,
        'image': image,
    }
    for record in records:
        notify_found_dog('Ufc5c40adb25791d5da4e25012b6023f8', record, founder)

    return create_response('ok', 200, 'successfully declare a found dog')

#TODO: PREM
# need to return breed as English (not Thai)
def predict_breed(image_url):
    breeds = ['Beagle', 'Poodle', 'Siberian Husky', 'Pug', 'Pomeranian', 'Shih-tzu', 'Golden Retriever', 'Corgi', 'Chihuahua', 'Bangkaew']
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
    address = None

    if request_data:
        if api_key.IMAGE in request_data:
            image = request_data[api_key.IMAGE]
        else:
            return create_response('error', 400, f'{api_key.IMAGE} was not found')

        if api_key.BREED in request_data:
            raw_breed = request_data[api_key.BREED]
            breed = map_breed(raw_breed)
            if breed == 'error':
                return create_response('error', 400, f'{raw_breed} does not support, please check spelling')
        else:
            return create_response('error', 400, f'{api_key.BREED} was not found')

        if api_key.LOCATION in request_data:
            lat = Decimal(request_data[api_key.LOCATION]['lat'])
            long = Decimal(request_data[api_key.LOCATION]['long'])
            address = request_data[api_key.LOCATION][api_key.ADDRESS]
            location= firestore.GeoPoint(lat, long)            
        else:
            return create_response('error', 400, f'{api_key.LOCATION} was not found')

        if 'case' in request_data:
            case = request_data['case']
        else:
            return create_response('error', 400, f'case was not found')

    dog = {
        'breed': breed,
        'image': image,
        'location': location,
        'address': address,
    }
    collection_group = None
    if case == 'lost':
        collection_group = firestore_collection.LOST_DOGS
    elif case == 'found':
        collection_group = firestore_collection.FOUND_DOGS
    else:
        return create_response('error', 400,  f'test API does not support case : {case}, it MUST be either lost or found')

    matchDf = None
    if case == 'lost':
        matchDf = scan_lost_dogs(dog)
    elif case == 'found':
        matchDf = scan_found_dogs(dog)

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

def scan_found_dogs(dog):
    print_heroku(dog)
    breed = dog['breed']
    docs = db.collection_group(firestore_collection.FOUND_DOGS).where('breed', '==', breed).get()
    print_heroku(f'there are {len(docs)} {breed} dogs in system')
    location = dog['location']
    lat = location.latitude
    long = location.longitude
    source = (lat, long)
    dataset = []
    for doc in docs:
        parent = doc.reference.parent.parent
        print_heroku(f'parent.id : {parent.id}')
        parent_data = parent.get().to_dict()
        data = doc.to_dict()
        print_heroku(f'{doc.id} => {data}')
        destination = (data['location'].latitude, data['location'].longitude)
        dist = distance.distance(source, destination).km # get distance between 2 geo points
        print_heroku(f'distance between dogs is {dist} km.')

        if (dist < RADIUS):
            row = {
                'dog_id': doc.id,
                'breed': data['breed'],
                'image': data['image'],
                'distance': dist,
                'founder': parent_data['display_name'],
                'phone': parent_data['phone'],
            }
            if 'name' in data:
                row['name'] = data['name']
            dataset.append(row)

    pd.set_option('display.width', 120)
    df = pd.DataFrame(dataset)
    print_heroku('printing data frame')
    print_heroku(df)
    matchDf = match_dogs(dog, df)
    return matchDf

def scan_lost_dogs(dog):
    print_heroku(dog)
    breed = dog['breed']
    docs = db.collection_group(firestore_collection.LOST_DOGS).where('breed', '==', breed).get()
    print_heroku(f'there are {len(docs)} {breed} dogs in system')
    location = dog['location']
    lat = location.latitude
    long = location.longitude
    source = (lat, long)
    dataset = []
    for doc in docs:
        parent = doc.reference.parent.parent
        print_heroku(f'parent.id : {parent.id}')
        parent_data = parent.get().to_dict()
        data = doc.to_dict()
        owner_ref = data['owner']       
        owner = owner_ref.get().to_dict()
        print('owner')
        print(owner)
        print_heroku(f'{doc.id} => {data}')
        destination = (data['location'].latitude, data['location'].longitude)
        dist = distance.distance(source, destination).km # get distance between 2 geo points
        print_heroku(f'distance between dogs is {dist} km.')

        if (dist < RADIUS):
            row = {
                'dog_id': doc.id,
                'name': data['name'],
                'breed': data['breed'],
                'image': data['image'],
                'distance': dist,
                'owner_name': owner['owner_name'],
                'phone': owner['phone'],
            }
            if 'name' in data:
                row['name'] = data['name']
            dataset.append(row)

    pd.set_option('display.width', 120)
    df = pd.DataFrame(dataset)
    print_heroku('printing data frame')
    print_heroku(df)
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

# new API
# https://dog-finder01.herokuapp.com/get-registered/{customer-id}


def print_heroku(message):
    print(message)
    sys.stdout.flush()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)