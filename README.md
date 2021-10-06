# DogFinderApi
APIs to register lost dogs and found dogs, the data will be collected in FireStore

### How to run
1. Need to install all needed libraries by using pip commands (you can see the list in `requirements.txt`)
2. **Need to get** `serviceAccountKey.json` **from the owner**
3. Run `python .\app.py` in the root directory
4. If everything is OK, you should be able to access http://localhost:5000/

## API Documents
### Register API
This is the API to register a lost dog before declaring the dog actually lost.  
**Parameters**  
- `customer_id ` line customer id
- `display_name` line customer display name
- `image` the image URL on s3 we get from Botnoi
- `breed` the dog breed
- `dog_name` the dog name
- `location` the lat, long coordination the dog/owner lives

**Return**
List of registered dog with following information
- `breed` the dog breed
- `dog_id` the generated dog id from Firebase
- `image` the dog image URL
- `lat` latitude
- `long` longitude
- `name` the dog name

Curl command
```
curl --location --request POST 'http://localhost:5000/register' \
--header 'Content-Type: application/json' \
--data-raw '    {
        "customer_id": "xxx-xxxx-xxxx-1",
        "display_name": "Godz",
        "image": "s3-image-url-from-botnoi",
        "dog_name": "dog2",
        "breed": "poodle",
        "location": {
            "lat": 13.942084564850742,
            "long": 100.55160812822899
        }
    }'
```    

### Get Registered Dog API
Get method API to get all registered dog from a given customer id.  
**Parameters**
- `customer_id` line customer id in query string

Curl command
```
curl --location --request GET 'http://localhost:5000/get-dogs/xxx-xxxx-xxxx-1'
```

### Declare Lost Dog API with pre-register
The API to declare the registered dog as lost (need to do the registration before).  
**Parameter**
- `customer_id` line customer id
- `dog_id` generated dog id  

**Return**
List of match dogs from found list. It can return empty list if there is no match dog at all.
- `dog_id` the generated id from Firebase
- `breed` the dog breed
- `image` the dog image URL
- `distance` the distance between the match dogs


Curl command
```
curl --location --request POST 'http://localhost:5000/lost-preregister' \
--header 'Content-Type: application/json' \
--data-raw '{
    "customer_id": "xxx-xxxx-xxxx-1",
    "dog_id": "lDO6Ml505Flk1486wkm"
}'
```

### Declar Lost Dog API without pre-register
The API to declare a dog as lost.  
**Parameter**
- `customer_id` line customer id
- `display_name` line customer display name
- `image` the image URL on s3 we get from Botnoi
- `dog_name` the dog name
- `breed` the dog breed
- `location` the lat, long coordination the dog/owner lives  

**Return**
List of match dogs from found list. It can return empty list if there is no match dog at all.
- `dog_id` the generated id from Firebase
- `breed` the dog breed
- `image` the dog image URL
- `distance` the distance between the match dogs

Curl command
```
curl --location --request POST 'http://localhost:5000/lost-register' \
--header 'Content-Type: application/json' \
--data-raw '    {
        "customer_id": "xxx-xxxx-xxxx-1",
        "display_name": "Godz",
        "image": "s3-image-url-from-botnoi",
        "dog_name": "dog1",
        "breed": "beagle",
        "location": {
            "lat": 13.942084564850742,
            "long": 100.55160812822899
        }
    }'
```

### Declare a found dog API
API to declare a found dog.
**Parameter**
- `customer_id` line customer id
- `display_name` line customer display name
- `image` the image URL on s3 we get from Botnoi
- `location` the lat, long coordination that user found the dog  

**Return**
List of match dogs from lost list. It can return empty list if there is no match dog at all.
- `dog_id` the generated id from Firebase
- `breed` the dog breed
- `image` the dog image URL
- `distance` the distance between the match dogs

Curl command
```
curl --location --request POST 'http://localhost:5000/found' \
--header 'Content-Type: application/json' \
--data-raw '    {
        "customer_id": "xxx-xxxx-found-5",
        "display_name": "Godz",
        "image": "s3-image-url-from-botnoi",
        "location": {
            "lat": 13.942084564850742,
            "long": 100.55160812822899
        }
    }'
```

### Test API
The API for testing scanning function. For example we have a lost dog, we would like to match found dogs or vice versa.
**Parameter**
- `case` found or lost, if case is found it means we're looking for lost dogs
- `breed` the dog breed
- `image` the dog image
- `location` the dog location as lat, long coordination

**Return**
List of match dogs. It can return empty list if there is no match dog at all.
- `dog_id` the generated id from Firebase
- `breed` the dog breed
- `image` the dog image URL
- `distance` the distance between the match dogs

Curl command
```
curl --location --request POST 'http://localhost:5000/test' \
--header 'Content-Type: application/json' \
--data-raw '{
    "case": "found",
    "breed": "chow chow",
    "image": "s3-image-url-from-botnoi",
    "location": {
        "lat": 13.893889357391064,
        "long": 100.56006330613269
    }
}'
```