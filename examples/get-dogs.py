import requests

customer_id = 'xxx-xxxx-xxxx-1'
r = requests.get('https://dog-finder01.herokuapp.com/get-dogs/' + customer_id)
print(r.status_code)
print(r.json())