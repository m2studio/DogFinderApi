import requests

r = requests.post('https://dog-finder01.herokuapp.com/lost-register', json= 
    {
        "customer_id": "xxx-xxxx-xxxx-2",
        "display_name": "Pao",
        "owner_name": "สมชาย เข็มกลัด",
        "phone": "0909998888",
        "image": "s3-image-url-from-botnoi",
        "dog_name": "dog1",
        "dog_gender": 0,
        "dog_age": "2-3",
        "breed": "พุดเดิ้ล",
        "location": {
            "lat": 13.942084564850742,
            "long": 100.55160812822899
        }
    }
)
print(r.status_code)
print(r.json())