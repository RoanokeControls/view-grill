import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
import pyrebase
import logging
from PyQt5.QtCore import QTimer

def get_firebase_data(mac_address, user, db):
    logging.debug(f"Fetching data for MAC address: {mac_address}")
    base_path = f"grills/{mac_address}/grill"
    try:
        grill_temp = db.child(base_path).child("G4/6").get(user['idToken']).val()
        logging.debug(f"Grill Temp: {grill_temp}")

        setpoint = db.child(base_path).child("G4/4").get(user['idToken']).val()
        logging.debug(f"Setpoint: {setpoint}")

        run_status = db.child(base_path).child("G4/1").get(user['idToken']).val()
        logging.debug(f"Run Status: {run_status}")

        logging.debug(f"Data fetched: Grill Temp: {grill_temp}, Setpoint: {setpoint}, Run Status: {run_status}")
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return {}

    return {
        "Grill Temp": grill_temp,
        "Setpoint": setpoint,
        "Run Status": run_status
    }

class MyApp(QWidget):
    def __init__(self, mac_address, user, db):
        super().__init__()
        self.mac_address = mac_address
        self.user = user
        self.db = db
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.titleLabel = QLabel(f"Monitoring device: {self.mac_address}", self)
        self.layout.addWidget(self.titleLabel)

        self.grillTempLabel = QLabel("Grill Temp: Loading...", self)
        self.layout.addWidget(self.grillTempLabel)

        self.setpointLabel = QLabel("Setpoint: Loading...", self)
        self.layout.addWidget(self.setpointLabel)

        self.runStatusLabel = QLabel("Run Status: Loading...", self)
        self.layout.addWidget(self.runStatusLabel)

        self.setLayout(self.layout)
        self.setWindowTitle('Grill Monitor')
        self.show()

        # Update data every X milliseconds (e.g., 5000ms = 5 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateData)
        self.timer.start(5000)

    def updateData(self):
        data = get_firebase_data(self.mac_address, self.user, self.db)
        self.grillTempLabel.setText(f"Grill Temp: {data.get('Grill Temp', 'N/A')}")
        self.setpointLabel.setText(f"Setpoint: {data.get('Setpoint', 'N/A')}")
        self.runStatusLabel.setText(f"Run Status: {data.get('Run Status', 'N/A')}")

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug("Starting the application")

    # Check for command line arguments
    if len(sys.argv) < 2:
        print("Usage: python view-grill.py <MAC_Address>")
        sys.exit(1)
    mac_address = sys.argv[1]

    # Firebase configuration - replace with your details
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
    db = firebase.database()

    # Authenticate
    user = auth.sign_in_with_email_and_password("tony@roanokecontrols.com", "matrix")

    app = QApplication(sys.argv)
    ex = MyApp(mac_address, user, db)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
