import pyrebase
import argparse
import logging
import matplotlib.pyplot as plt
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

class PlotWindow(QMainWindow):
    def __init__(self, status_counts):
        super().__init__()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        self.plot_status_ratios(status_counts)

    def plot_status_ratios(self, status_counts):
        labels = status_counts.keys()
        sizes = status_counts.values()

        self.ax.clear()
        self.ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
        self.ax.set_title("Grill Status Ratios")
        self.canvas.draw()

def analyze_grill_statuses(db, user):
    status_counts = {"BURNING": 0, "OFF AND COOL": 0, "SHUTDOWN": 0}
    
    try:
        grills = db.child("grills").get(user['idToken'])
        for grill in grills.each():
            run_status = grill.val().get("Run Status")
            if run_status in status_counts:
                status_counts[run_status] += 1
            else:
                logging.warning(f"Unknown status '{run_status}' found for grill {grill.key()}")
                
        logging.debug(f"Status counts: {status_counts}")
        return status_counts
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return status_counts
    
def plot_status_ratios(status_counts):
    # Clean the data: Remove non-numeric or negative values
    cleaned_counts = {k: (v if np.isfinite(v) and v >= 0 else 0) for k, v in status_counts.items()}

    # Extract labels and sizes
    labels = list(cleaned_counts.keys())
    sizes = list(cleaned_counts.values())

    # Ensure the sizes sum up to more than zero
    if sum(sizes) <= 0:
        logging.warning("No valid data to plot.")
        return

    # Debugging: Print data to be plotted
    logging.debug(f"Labels: {labels}, Sizes: {sizes}")

    # Plot the Pie chart
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')  # Ensures the pie chart is circular
    plt.title("Grill Status Ratios")
    plt.show()

# Set up command line argument parsing
parser = argparse.ArgumentParser()
parser.add_argument("--debug", help="Enable debug mode", action="store_true")
args = parser.parse_args()

# Configure logging
if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

def find_burning_grills(db, user):
    try:
        grills = db.child("grills").get(user['idToken'])
        total_grills = 0
        burning_grills = 0

        for grill in grills.each():
            mac_address = grill.key()
            total_grills += 1

            # Path to access the run status
            run_status_path = f"grills/{mac_address}/grill/G4/1"
            run_status_code_raw = db.child(run_status_path).get(user['idToken']).val()

            # Process the run status code
            run_status_code = run_status_code_raw.strip() if isinstance(run_status_code_raw, str) else run_status_code_raw

            # Define run states
            run_states = {
                "0": "OFF AND COOL",
                "1": "BURNING",
                "2": "SHUTDOWN"
            }

            run_status = run_states.get(run_status_code, "UNKNOWN")

            # Check if the run status is 'BURNING'
            if run_status == "BURNING":
                burning_grills += 1
                # logging.info(f"Grill Burning: {mac_address}")  # Output the MAC address

        logging.debug(f"Total grills scanned: {total_grills}")
        logging.debug(f"Total grills burning: {burning_grills}")
    except Exception as e:
        logging.error(f"Error fetching data: {e}")


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

# Analyze grill statuses
status_counts = analyze_grill_statuses(db, user)

# Plot the status ratios
plot_status_ratios(status_counts)


if __name__ == '__main__':
    # ... setup code ...

    app = QApplication(sys.argv)
    status_counts = analyze_grill_statuses(db, user)

    if status_counts and sum(status_counts.values()) > 0:
        mainWin = PlotWindow(status_counts)
        mainWin.show()
        sys.exit(app.exec_())
    else:
        logging.warning("No valid grill status data available for plotting.")