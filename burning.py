import sys
import logging
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
import pyrebase
import threading
import datetime
import pytz
from PyQt5.QtCore import QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import matplotlib.dates as mdates

# Configure the logging module
logging.basicConfig(level=logging.DEBUG)  # Set the default logging level to DEBUG

def is_online(timestamp_str):
    try:
        # Define the GMT timezone
        gmt = pytz.timezone('GMT')

        # Parse the timestamp string into a datetime object in GMT
        timestamp = gmt.localize(datetime.datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S'))

        # Get the current time in GMT
        current_time = datetime.datetime.now(datetime.timezone.utc)

        # Calculate the time difference
        time_difference = current_time - timestamp

        if(time_difference.total_seconds() <= 120):  # 120 seconds = 2 minutes
            logging.debug(f"Grill is online, time difference is: {time_difference.total_seconds()} seconds")

        # Check if the time difference is less than 2 minutes
        return time_difference.total_seconds() <= 120
    except Exception as e:
        logging.error(f"Error processing timestamp for online status: {e}")
        return False

def is_within_last_24_hours(timestamp_str):
    try:
        # Define the GMT timezone
        gmt = pytz.timezone('GMT')

        # Parse the timestamp string into a datetime object in GMT
        timestamp = gmt.localize(datetime.datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S'))

        # Get the current time in GMT
        current_time = datetime.datetime.now(datetime.timezone.utc)

        # Calculate the time difference
        time_difference = current_time - timestamp

        if(time_difference.total_seconds() <= 24 * 60 * 60):
            logging.debug(f"Time difference is: {time_difference.total_seconds()}")

        # Check if the time difference is less than 24 hours
        return time_difference.total_seconds() <= 24 * 60 * 60  # 24 hours in seconds
    except Exception as e:
        logging.error(f"Error processing timestamp: {e}")
        return False  # Handle errors gracefully
    
class GrillMonitorApp(QWidget):
    def __init__(self, db, user):
        super().__init__()
        self.db = db
        self.user = user

        self.initialPlotDone = False  # Flag to track if initial plot is done
       
        self.onlineGrillsData = []  # Store data points here
        self.onlineGrills = 0  # Initialize the onlineGrills attribute
        self.onlineGrillsData = [(datetime.datetime.now(), 0)]  # Initialize with the current time and zero online grills

        self.initUI()
        self.startGrillScanning()

        # Setup a QTimer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.findBurningGrills)
        self.timer.start(300000)  # 300000 milliseconds = 5 minutes

    

    def initUI(self):
        self.layout = QVBoxLayout(self)

        self.totalGrillsLabel = QLabel("Total Grills Scanned: 0", self)
        self.layout.addWidget(self.totalGrillsLabel)

        self.burningGrillsLabel = QLabel("Total Grills Burning: 0", self)
        self.layout.addWidget(self.burningGrillsLabel)

        # New label for online grills
        self.onlineGrillsLabel = QLabel("Total Online Grills: 0", self)
        self.layout.addWidget(self.onlineGrillsLabel)

        # Matplotlib figure
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        self.setLayout(self.layout)
        self.setWindowTitle('Grill Monitor')
        self.resize(800, 600)  # Adjust size as needed
        self.show()

    def startGrillScanning(self):
        # Start the initial scanning in a new thread
        threading.Thread(target=self.findBurningGrills, daemon=True).start()


    def findBurningGrills(self):
        try:
            total_grills = 0
            burning_grills = 0
            online_grills = 0

            # Retrieve all grills
            grills_query = self.db.child("grills").get(self.user['idToken']).val()

            if grills_query:
                for mac_address, grill_data in grills_query.items():
                    total_grills += 1

                    if 'grill' in grill_data and 'G4' in grill_data['grill']:
                        g4_data = grill_data['grill']['G4']
                        if len(g4_data) >= 2:
                            g4_1_value = str(g4_data[1]).strip()
                            
                            if g4_1_value == "1":
                                burning_grills += 1

                    if 'grill' in grill_data and 'timeStamp' in grill_data['grill']:
                        timestamp_str = grill_data['grill']['timeStamp']
                        if is_online(timestamp_str):
                            online_grills += 1

                # Update UI
                self.totalGrillsLabel.setText(f"Total Grills Scanned: {total_grills}")
                self.burningGrillsLabel.setText(f"Total Grills Burning: {burning_grills}")
                self.onlineGrillsLabel.setText(f"Total Online Grills: {online_grills}")

                # Update the onlineGrillsData list with the new count of online grills
                self.onlineGrills = online_grills
                self.onlineGrillsData.append((datetime.datetime.now(), self.onlineGrills))

                # Check if initial plot is done
                if not self.initialPlotDone:
                    self.updatePlot()
                    self.initialPlotDone = True
                else:
                    self.updatePlot()

        except Exception as e:
            logging.error(f"Error fetching data: {e}")

    def updatePlot(self):
        # Clear the current plot
        self.figure.clear()

        # Create the new plot
        ax = self.figure.add_subplot(111)

        # Plot the data
        ax.plot(
            [point[0] for point in self.onlineGrillsData],  # X-axis: Time
            [point[1] for point in self.onlineGrillsData],  # Y-axis: Number of online grills
            marker='o'
        )

        # Format plot (e.g., labels, title)
        ax.set_title("Number of Online Grills Over Time")
        ax.set_xlabel("Time (15-Min Intervals)")
        ax.set_ylabel("Online Grills")

        # Format the x-axis to show time with 15-minute granularity
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # Show hours and minutes
        ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0, 60, 15)))  # 15-minute intervals

        # Set y-axis limits if needed
        y_min = min(point[1] for point in self.onlineGrillsData)
        y_max = max(point[1] for point in self.onlineGrillsData)
        if y_min == y_max:
            y_buffer = 1 if y_min == 0 else y_min * 0.1
            ax.set_ylim(y_min - y_buffer, y_max + y_buffer)
        else:
            ax.set_ylim(y_min, y_max)

        # Draw the plot
        self.canvas.draw()
        
def test_firebase_connection(db, user_id_token):
    try:
        # Replace 'path/to/known/value' with the path to a known value in your Firebase database
        test_value = db.child("grills/94:B9:7E:48:B0:C0").get(user_id_token).val()
        if test_value is not None:
            logging.info(f"Successfully retrieved data: {test_value}")
            return True
        else:
            logging.error("Failed to retrieve data: Known value is None.")
            return False
    except Exception as e:
        logging.error(f"Error retrieving data: {e}")
        return False

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

    # Function to authenticate
    def authenticate():
        try:
            user = auth.sign_in_with_email_and_password("tony@roanokecontrols.com", "matrix")
            logging.info("Authentication successful.")
            return user
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            return None

    # Authenticate for the first time
    user = authenticate()
    if not user:
        return  # Exit if initial authentication fails

    # Test Firebase connection and re-authenticate if necessary
    def test_and_reauthenticate():
        if not test_firebase_connection(db, user['idToken']):
            logging.warning("Attempting to re-authenticate due to permission error.")
            return authenticate()
        return user

    # Start the application
    app = QApplication(sys.argv)
    ex = GrillMonitorApp(db, test_and_reauthenticate())
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()