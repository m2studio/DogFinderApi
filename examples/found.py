import requests

r = requests.post('https://dog-finder01.herokuapp.com/found', json= 
    {
        "customer_id": "xxx-xxxx-found-7",
        "display_name": "founder7",
        "image": "s3-image-url-from-botnoi",
        "location": {
            "lat": 13.942084564850742,
            "long": 100.55160812822899
        }
    }
)
print(r.status_code)
print(r.json())