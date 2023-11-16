import pyrebase

def stream_handler(message):
    print(message["event"])  # put, patch, etc
    print(message["path"])   # path to the data
    print(message["data"])   # actual data


def test_firebase_fetch():


    config = {
        "apiKey": "AIzaSyBTyhoMOahtIkb4CRg9sMZm8XRTBtOh6jE",
        "authDomain": "rec-push-test.firebaseapp.com",
        "databaseURL": "https://rec-push-test.firebaseio.com",
        "projectId": "rec-push-test",
        "storageBucket": "rec-push-test.appspot.com",
        "messagingSenderId": "523654118523",
        "appId": "1:523654118523:web:1149c26a6af2f88bac76de",
        "measurementId": "G-B276K0J39X"
    }

    # Initialize Firebase
    firebase = pyrebase.initialize_app(config)
    auth = firebase.auth()
  
    user = auth.sign_in_with_email_and_password("tony@roanokecontrols.com", "matrix")
    db = firebase.database()
    

    # Fetch the first 5 records, ordered by key
    grills = db.child("grills").order_by_key().limit_to_first(5).get(user['idToken']).val()
    for key, value in grills.items():
        print(f"{key}: {value}")

if __name__ == '__main__':
    test_firebase_fetch()