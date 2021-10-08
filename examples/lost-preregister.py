import requests

r = requests.post('https://dog-finder01.herokuapp.com/lost-preregister', json= 
    {
    "customer_id": "xxx-xxxx-xxxx-1",
    "dog_id": "h9YCNMw66OUFVEYvC1En", # need to use correct dog_id (it's auto generated if from Firestore)
    "phone": "0847485152",
    "location": {
        "lat": 13.942084564850742,
        "long": 100.55160812822899
    }
}
)
print(r.status_code)
print(r.json())