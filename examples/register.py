import requests

r = requests.post('https://dog-finder01.herokuapp.com/register', json= 
    {
        "customer_id": "xxx-xxxx-xxxx-4",
        "display_name": "Chris",
        "owner_name": "คริส ไซเรนเซอร์",
        "image": "s3-image-url-from-botnoi",
        "dog_name": "dog",
        "dog_age": "0-9",
        "dog_gender": 0,
        "breed": "บีเกิ้ล"
    }
)
print(r.status_code)
print(r.json())