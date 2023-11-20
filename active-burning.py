import sys
import logging
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
import pyrebase
import threading
import datetime
import pytz

# Configure the logging module
logging.basicConfig(level=logging.DEBUG)  # Set the default logging level to DEBUG

def is_within_last_24_hours(timestamp):
    try:
        gmt = pytz.timezone('GMT')

        # If timestamp is a string, convert it to datetime
        if isinstance(timestamp, str):
            # Parse the timestamp string into a datetime object in GMT
            timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            # Localize the timestamp to GMT
            timestamp = gmt.localize(timestamp)

        # If timestamp is already a datetime object but is naive, localize it to GMT
        elif isinstance(timestamp, datetime.datetime) and timestamp.tzinfo is None:
            timestamp = gmt.localize(timestamp)

        # Get the current time in GMT as an aware datetime object
        current_time = datetime.datetime.now(datetime.timezone.utc)

        # Calculate the time difference
        time_difference = current_time - timestamp

        logging.debug(f"Time difference is: {time_difference.total_seconds()}")

        # Check if the time difference is less than 24 hours
        return time_difference.total_seconds() <= 24 * 60 * 60  # 24 hours in seconds
    except Exception as e:
        logging.error(f"Error processing timestamp: {e}")
        return False


class GrillMonitorApp(QWidget):
    def __init__(self, db, user):
        super().__init__()
        self.db = db
        self.user = user

        self.initUI()
        self.startGrillScanning()

    def startGrillScanning(self):
        threading.Thread(target=self.findRecentGrills, daemon=True).start()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # Label to display the total number of grills scanned
        self.totalGrillsLabel = QLabel("Total Grills Scanned: 0", self)
        self.layout.addWidget(self.totalGrillsLabel)

        # Update this label to reflect recent activity instead of just burning grills
        self.recentGrillsLabel = QLabel("Total Grills with Recent Activity: 0", self)
        self.layout.addWidget(self.recentGrillsLabel)

        self.setLayout(self.layout)
        self.setWindowTitle('Grill Monitor - Recent Activity')
        self.show()


    def startGrillScanning(self):
        # Start the scanning in a new thread
        threading.Thread(target=self.findRecentGrills, daemon=True).start()

    def findRecentGrills(self):
        try:
            total_grills = 0
            recent_grills = 0

            # Retrieve all grills from Firebase
            grills_query = self.db.child("grills").get(self.user['idToken']).val()

            if grills_query:
                for mac_address, grill_data in grills_query.items():
                    logging.debug(f"Checking grill: {mac_address}")

                    # Check if 'grill' key exists and 'timeStamp' is within 'grill'
                    if 'grill' in grill_data and 'timeStamp' in grill_data['grill']:
                        timestamp = grill_data['grill']['timeStamp']
                        logging.debug(f"Original timestamp for {mac_address}: {timestamp}")

                        # Check if the timestamp is a string
                        if isinstance(timestamp, str):
                            try:
                                # Convert the string to a datetime object
                                timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                logging.error(f"Malformed timestamp string for {mac_address}: {timestamp}")
                                continue

                        # If the timestamp is already a datetime object, directly check if it's within the last 24 hours
                        if isinstance(timestamp, datetime.datetime):
                            if is_within_last_24_hours(timestamp):
                                recent_grills += 1
                                logging.debug(f"Grill {mac_address} has recent activity. Timestamp: {timestamp}")
                            else:
                                logging.debug(f"Grill {mac_address} does not have recent activity. Timestamp: {timestamp}")
                        else:
                            logging.error(f"Unexpected timestamp type for {mac_address}: {type(timestamp)}")

                    else:
                        logging.warning(f"Timestamp data missing or not in expected format for {mac_address}. Grill data: {grill_data}")
                        total_grills += 1
                        continue

                    total_grills += 1

                # Update UI
                self.totalGrillsLabel.setText(f"Total Grills Scanned: {total_grills}")
                self.recentGrillsLabel.setText(f"Total Grills with Recent Activity: {recent_grills}")

        except Exception as e:
            logging.error(f"Error fetching data: {e}")


def main():
    # Parse command-line arguments
    debug_mode = '--debug' in sys.argv

    # Configure the logging level based on whether --debug is provided
    if debug_mode:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    # Firebase configuration
    config = {
        # Your Firebase configuration here
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
    try:
        user = auth.sign_in_with_email_and_password("tony@roanokecontrols.com", "matrix")
        logging.info("Authentication successful.")
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        return  # Exit if authentication fails

    # Start the application
    app = QApplication(sys.argv)
    ex = GrillMonitorApp(db, user)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()