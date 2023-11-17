import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QLineEdit, QComboBox, QMessageBox
import pyrebase
import logging
from PyQt5.QtCore import QTimer
import argparse
import pytz
import re
import json
from datetime import datetime, timedelta
# from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QComboBox, QLineEdit, QPushButton
# from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from matplotlib.dates import DateFormatter


class MyApp(QWidget):
    def __init__(self, mac_address, user, db):
        super().__init__()
        self.mac_address = mac_address
        self.user = user
        self.db = db
        

         # Initialize data lists for plotting
        self.x_data = []
        self.y_data = []
        
        self.initUI()  # Initialize the UI before calling updateData
        self.loadMacAddresses()  # Load MAC addresses first
        self.updateData()  # Now it's safe to call updateData

        # Add the command line MAC address to the list if not already present
        if self.mac_address and self.mac_address not in self.macAddresses:
            self.macAddresses.append(self.mac_address)
            self.macComboBox.addItem(self.mac_address)
            self.saveMacAddresses()  # Save the updated list
        

    def get_firebase_data(self, mac_address, user, db):
        logging.debug(f"Fetching data for MAC address: {mac_address}")
        base_path = f"grills/{mac_address}/grill"
        try:
            grill_temp = db.child(base_path).child("G4/6").get(user['idToken']).val()
            setpoint = db.child(base_path).child("G4/4").get(user['idToken']).val()
            run_status_code_raw = db.child(base_path).child("G4/1").get(user['idToken']).val()
            run_status_code = run_status_code_raw.strip() if isinstance(run_status_code_raw, str) else run_status_code_raw
            logging.debug(f"Run Status Code (Processed): '{run_status_code}' (Length: {len(str(run_status_code))})")
            timeStamp = db.child(base_path).child("timeStamp").get(user['idToken']).val()
            run_states = {
                "0": "OFF AND COOL",
                "1": "BURNING",
                "2": "SHUTDOWN"
            }
            run_status = run_states.get(str(run_status_code), "UNKNOWN")
            ssid = db.child(base_path).child("debugData/parmlist/0/ssid").get(user['idToken']).val()
            rssi = db.child(base_path).child("debugData/parmlist/0/rssi").get(user['idToken']).val()
            ipaddress = db.child(base_path).child("ipAddress").get(user['idToken']).val()
            logging.debug(f"Final Run Status: {run_status}")
            logging.debug(f"Data fetched: Grill Temp: {grill_temp}, Setpoint: {setpoint}, Run Status: {run_status}, TimeStamp: {timeStamp}")
        except Exception as e:
            logging.error(f"Error fetching data: {e}")
            return {}

        return {
            "Grill Temp": grill_temp,
            "Setpoint": setpoint,
            "Run Status": run_status,
            "TimeStamp": timeStamp,
            "SSID": ssid,
            "RSSI": rssi,
            "IPAddress": ipaddress
        }

    def getTemperatureData(self, mac_address):
        try:
            temp_data_path = f"grills/{mac_address}/grill/G4/6"
            timestamp_path = f"grills/{mac_address}/grill/timeStamp"

            temperature_data = self.db.child(temp_data_path).get(self.user['idToken']).val()
            timestamp_data = self.db.child(timestamp_path).get(self.user['idToken']).val()

            if temperature_data is not None and timestamp_data is not None:
                temperature_value = float(temperature_data)
                time_value = datetime.strptime(timestamp_data, '%Y-%m-%d %H:%M:%S').time()
                return (time_value, temperature_value)
            else:
                return (None, None)
        except Exception as e:
            print(f"Error fetching data for grill {mac_address}: {e}")
            return None, None


            
    def updatePlot(self, time_value, temperature):
        # Clear the current axes, preserving the figure
        self.figure.clf()
        ax = self.figure.add_subplot(111)

        # Convert time to a format that can be plotted
        time_for_plot = mdates.date2num(datetime.combine(datetime.today(), time_value))

        # Append new data to your existing data lists
        self.x_data.append(time_for_plot)
        self.y_data.append(temperature)

        ax.plot_date(self.x_data, self.y_data, '-')  # Use plot_date for time data
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        ax.set_title('Grill Temperature Over Time')
        ax.set_xlabel('Time')
        ax.set_ylabel('Temperature')
        ax.relim()
        ax.autoscale_view()

        # Redraw the canvas after updating
        self.canvas.draw()

    def getLastUsedMacAddress(self):
        try:
            with open('last_mac.json', 'r') as file:
                return json.load(file).get('last_mac', '')
        except (FileNotFoundError, json.JSONDecodeError):
            return ''
        
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

        self.timeStampLabel = QLabel("TimeStamp: Loading...", self)
        self.layout.addWidget(self.timeStampLabel)

        self.timeElapsedLabel = QLabel("", self)
        self.timeElapsedLabel.hide()
        self.layout.addWidget(self.timeElapsedLabel)

        # Spacer
        self.layout.addWidget(QLabel(" "))  # Empty QLabel as a spacer

        # New Labels
        self.ssidLabel = QLabel("SSID: ", self)
        self.rssiLabel = QLabel("RSSI: ", self)
        self.ipaddressLabel = QLabel("Status: Loading...", self)

        # Initially hide SSID and RSSI labels
        self.ssidLabel.hide()
        self.rssiLabel.hide()

        self.layout.addWidget(self.ipaddressLabel)
        self.layout.addWidget(self.ssidLabel)
        self.layout.addWidget(self.rssiLabel)

        self.macInput = QLineEdit(self)
        self.layout.addWidget(self.macInput)

        self.macComboBox = QComboBox(self)
        self.layout.addWidget(self.macComboBox)
        self.macComboBox.activated[str].connect(self.onMacSelected)  # Connect dropdown selection event
       
        self.macSubmitButton = QPushButton('Connect', self)
        self.macSubmitButton.clicked.connect(self.submitMacAddress)
        self.layout.addWidget(self.macSubmitButton)
        
        self.quitButton = QPushButton('Quit', self)
        self.quitButton.clicked.connect(self.close)
        self.layout.addWidget(self.quitButton)

       # Create a matplotlib figure and canvas only if not already created
        if not hasattr(self, 'figure'):
            self.figure = plt.figure()
            self.canvas = FigureCanvas(self.figure)
            self.layout.addWidget(self.canvas)  # Add canvas to your layout
        else:
            print("Figure and canvas already initialized.")

        self.setLayout(self.layout)
        self.setWindowTitle('Grill Monitor')
        self.show()

        self.updateData()

        # Set up a QTimer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateData)
        self.timer.start(5000)  # Update every 5000 milliseconds (5 seconds)


    def saveLastUsedMacAddress(self, mac_address):
        with open('last_mac.json', 'w') as file:
            json.dump({'last_mac': mac_address}, file)

    def onMacSelected(self, text):
        # Check if the selected MAC address is valid
        if self.isValidMacAddress(text):
            self.mac_address = text
            self.titleLabel.setText(f"Monitoring device: {self.mac_address}")
            self.updateData()  # Fetch and update data for the new MAC address

            # Save as the last used MAC address
            self.saveLastUsedMacAddress(self.mac_address)
        else:
            QMessageBox.warning(self, "Invalid MAC Address", "The selected MAC address is invalid.")

    def submitMacAddress(self):
        mac_address = self.macInput.text().strip()
        # Convert hyphens to colons
        mac_address = mac_address.replace("-", ":")

        # If the text field is empty, use the selected item from the combo box
        if not mac_address:
            mac_address = self.macComboBox.currentText()

        # Proceed only if the MAC address is valid
        if mac_address and self.isValidMacAddress(mac_address):
            self.mac_address = mac_address
            self.titleLabel.setText(f"Monitoring device: {mac_address}")
            self.updateData()  # Fetch and update data for the new MAC address

            # Save as the last used MAC address
            self.saveLastUsedMacAddress(mac_address)

            # Update the list and combo box
            if mac_address not in self.macAddresses:
                self.macAddresses.append(mac_address)
                self.macComboBox.addItem(mac_address)
                self.saveMacAddresses()
            else:
                # Update the combo box if the MAC address was previously in a different format
                index = self.macComboBox.findText(mac_address)
                if index >= 0:
                    self.macComboBox.setItemText(index, mac_address)

        else:
            # Show dialog box for invalid MAC address format and do not connect
            QMessageBox.warning(self, "Invalid MAC Address", "The entered MAC address format is invalid.")
            self.macInput.setFocus()  # Optionally set focus back to input field


    def isValidMacAddress(self, mac):
        pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        return pattern.match(mac) is not None
    
    def saveMacAddresses(self):
        with open('mac_addresses.json', 'w') as file:
            json.dump(self.macAddresses, file)
            
    def isValidMac(self, mac):
        # Add logic to validate MAC address format
        return True  # Placeholder, replace with actual validation logic

    def loadMacAddresses(self):
        try:
            with open('mac_addresses.json', 'r') as file:
                mac_addresses = json.load(file)

            # Filter the list to include only valid MAC addresses
            valid_mac_addresses = [mac for mac in mac_addresses if self.isValidMacAddress(mac)]

            if len(valid_mac_addresses) != len(mac_addresses):
                # Update the file if invalid MAC addresses were found
                with open('mac_addresses.json', 'w') as file:
                    json.dump(valid_mac_addresses, file)

            self.macAddresses = valid_mac_addresses
            self.macComboBox.clear()
            self.macComboBox.addItems(self.macAddresses)

        except (FileNotFoundError, json.JSONDecodeError):
            self.macAddresses = []

    def submitMacAddress(self):
        mac_address = self.macInput.text().strip()

        # If the text field is empty, use the selected item from the combo box
        if not mac_address:
            mac_address = self.macComboBox.currentText()

        # Proceed only if the MAC address is valid
        if mac_address and self.isValidMacAddress(mac_address):
            self.mac_address = mac_address
            self.titleLabel.setText(f"Monitoring device: {mac_address}")
            self.updateData()  # Fetch and update data for the new MAC address

            # Save as the last used MAC address
            self.saveLastUsedMacAddress(mac_address)

            # Remove the MAC address from the list if it's already there
            if mac_address in self.macAddresses:
                self.macAddresses.remove(mac_address)
                self.macComboBox.removeItem(self.macComboBox.findText(mac_address))
            
            # Add the MAC address to the beginning of the list
            self.macAddresses.insert(0, mac_address)
            self.macComboBox.insertItem(0, mac_address)
            self.macComboBox.setCurrentIndex(0)  # Set the current index to the first item

            # Save the updated list
            self.saveMacAddresses()
        else:
            # Show dialog box for invalid MAC address format and do not connect
            QMessageBox.warning(self, "Invalid MAC Address", "The entered MAC address format is invalid.")
            self.macInput.setFocus()  # Optionally set focus back to input field
      
    def updateData(self):
        data = self.get_firebase_data(self.mac_address, self.user, self.db)

        # Update Grill Temp and Setpoint
        grill_temp = data.get("Grill Temp", "Loading...")
        setpoint = data.get("Setpoint", "Loading...")
        self.grillTempLabel.setText(f"Grill Temp: {grill_temp}")
        self.setpointLabel.setText(f"Setpoint: {setpoint}")
        
        # Run Status Check
        run_status = data.get("Run Status")
        if run_status == "OFF AND COOL" or run_status == "SHUTDOWN":
            self.grillTempLabel.hide()
            self.setpointLabel.hide()
            self.canvas.hide()  # Hide the plot
            self.resize(400, 300)  # Smaller size for SHUTDOWN mode
        else:
            # Update Grill Temp and Setpoint
            grill_temp = data.get("Grill Temp", "Loading...")
            setpoint = data.get("Setpoint", "Loading...")
            self.grillTempLabel.setText(f"Grill Temp: {grill_temp}")
            self.setpointLabel.setText(f"Setpoint: {setpoint}")
            self.grillTempLabel.show()
            self.setpointLabel.show()

            if run_status == "BURNING":
                # Fetch temperature data and update the plot
                time_value, temperature = self.getTemperatureData(self.mac_address)
                if time_value is not None and temperature is not None:
                    self.updatePlot(time_value, temperature)
                    self.canvas.show()  # Show the plot
                    self.resize(800, 600)  # Larger size to accommodate plot

        ssid = data.get("SSID")
        logging.debug(f"Checking SSID: {ssid}")
        if ssid is None or ssid == "None":
            logging.debug("Hiding RSSI label")
            self.ssidLabel.setText("SSID: Not Connected")
            self.ssidLabel.show()
            self.rssiLabel.hide()
        else:
            rssi = data.get("RSSI", "N/A")
            self.ssidLabel.setText(f"SSID: {ssid}")
            self.rssiLabel.setText(f"RSSI: {rssi}")
            self.ssidLabel.show()
            self.rssiLabel.show()

        self.runStatusLabel.setText(f"Run Status: {data.get('Run Status', 'N/A')}")
        timeStamp = data.get('TimeStamp')

        if timeStamp:
            self.timeStampLabel.setText(f"TimeStamp: {timeStamp}")
        else:
            self.timeStampLabel.setText("TimeStamp: N/A")

        try:
            last_seen_str = data.get('TimeStamp')
            if last_seen_str:
                last_seen = datetime.strptime(last_seen_str, '%Y-%m-%d %H:%M:%S')
                logging.debug(f"Last Seen: {last_seen}")

                # Get the current time in GMT
                now = datetime.utcnow()
                logging.debug(f"Now (GMT): {now}")

                diff = now - last_seen
                logging.debug(f"Difference: {diff}")

                # Check if the difference is more than an hour
                if diff > timedelta(hours=1):
                    self.ipaddressLabel.setText("Status: OFFLINE")
                    self.ipaddressLabel.setStyleSheet("color: red;")
                    elapsed_time = str(diff).split('.')[0]  # Format as days, hours, minutes, seconds
                    self.timeElapsedLabel.setText(f"Last seen: {elapsed_time} ago")
                    self.timeElapsedLabel.show()
                    self.ssidLabel.hide()
                    self.rssiLabel.hide()
                else:
                    # Existing code to update IP address, SSID, and RSSI labels
                    self.ipaddressLabel.setText(f"IPAddress: {data.get('IPAddress', 'N/A')}")
                    self.ipaddressLabel.setStyleSheet("color: white;")
                    self.ssidLabel.setText(f"SSID: {data.get('SSID', 'N/A')}")
                    self.rssiLabel.setText(f"RSSI: {data.get('RSSI', 'N/A')}")
                    self.ssidLabel.show()
                    self.rssiLabel.show()
                    self.timeElapsedLabel.hide()
            else:
                # Handle missing timeStamp
                self.ipaddressLabel.setText("Status: UNKNOWN")
                self.ipaddressLabel.setStyleSheet("color: orange;")
                self.timeElapsedLabel.hide()
                self.ssidLabel.hide()
                self.rssiLabel.hide()

        except ValueError:
            # Handle invalid timeStamp format
            self.ipaddressLabel.setText("Status: UNKNOWN")
            self.ipaddressLabel.setStyleSheet("color: orange;")
            self.timeElapsedLabel.hide()
            self.ssidLabel.hide()
            self.rssiLabel.hide()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mac_address", help="MAC address of the device")
    parser.add_argument("--debug", help="Enable debug mode", action="store_true")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug("Starting the application")
    mac_address = args.mac_address

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
    # No need to pass arguments to updateData here because it will use the instance attributes.
    ex.updateData()  # Corrected call without additional arguments
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()