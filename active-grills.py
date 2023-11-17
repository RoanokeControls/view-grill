import pyrebase


def find_burning_grills(db, user):
    try:
        # Fetch all grills with authenticated user token
        grills = db.child("grills").get(user['idToken'])

        # Check each grill for BURNING status
        for grill in grills.each():
            run_status = grill.val().get("Run Status")
            if run_status == "BURNING":
                print(f"Grill Burning: {grill.key()}")  # Output the MAC address
    except Exception as e:
        print(f"Error fetching data: {e}")

# Firebase configuration
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

# Authenticate
user = auth.sign_in_with_email_and_password("tony@roanokecontrols.com", "matrix")
db = firebase.database()

# Pass the authenticated database reference to the function
find_burning_grills(db, user)

