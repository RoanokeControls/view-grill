import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
import pyrebase
import threading

class GrillMonitorApp(QWidget):
    def __init__(self, db, user):
        super().__init__()
        self.db = db
        self.user = user

        self.initUI()
        self.startGrillScanning()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        self.totalGrillsLabel = QLabel("Total Grills Scanned: 0", self)
        self.layout.addWidget(self.totalGrillsLabel)

        self.burningGrillsLabel = QLabel("Total Grills Burning: 0", self)
        self.layout.addWidget(self.burningGrillsLabel)

        self.setLayout(self.layout)
        self.setWindowTitle('Grill Monitor')
        self.show()

    def startGrillScanning(self):
        # Start the scanning in a new thread
        threading.Thread(target=self.findBurningGrills, daemon=True).start()

    def findBurningGrills(self):
        try:
            grills = self.db.child("grills").get(self.user['idToken'])
            total_grills = 0
            burning_grills = 0

            for grill in grills.each():
                mac_address = grill.key()
                total_grills += 1

                # Fetch run status using the correct path
                run_status_code_raw = self.db.child(f"grills/{mac_address}/grill/G4/1").get(self.user['idToken']).val()
                run_status_code = run_status_code_raw.strip() if isinstance(run_status_code_raw, str) else run_status_code_raw
        
                # Check if the run status is '1' for BURNING
                if run_status_code == "1":
                    burning_grills += 1

                # Update UI
                self.totalGrillsLabel.setText(f"Total Grills Scanned: {total_grills}")
                self.burningGrillsLabel.setText(f"Total Grills Burning: {burning_grills}")
                QApplication.processEvents()

        except Exception as e:
            print(f"Error fetching data: {e}")

def main():
    # Firebase configuration
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

    app = QApplication(sys.argv)
    ex = GrillMonitorApp(db, user)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
