import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

#TODO API for registration
# add documents to a collection with auto ID
# data = {'name': 'John', 'age': 40}
# db.collection('persons').add(data)  # it equals to db.collection('persons').document().set(data)

# set documents with known ID
# db.collection('persons').document('john').set(data) # document reference

# add subdocument
# db.collection('persons').document('john').collection('movies').add({'name': 'Avengers'})


# Query
# Getting a document with a known ID
# result = db.collection('persons').document('john').get()

# if result.exists:
#     print(result.to_dict())
# else:
#     print('document does not exist')


# Get all documents in a collection
print('get all documents')
docs = db.collection('persons').get()
for doc in docs:
    print(doc.to_dict())

print('get documents age > 30')
docs = db.collection('persons').where('age', '>', 30).get()
# docs = db.collection('persons').where('name', '==', 'John').get()
for doc in docs:
    print(doc.to_dict())

# query array
# docs = db.collection('persons').where('socials', 'array_contains', 'youtube').get()

# in operator
# docs = db.collection('persons').where('addres', 'in', ['London', 'Milan']).get()

