import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QLineEdit, QComboBox
import pyrebase
import logging
from PyQt5.QtCore import QTimer
import argparse
import pytz
import re

import json

from datetime import datetime, timedelta


def get_firebase_data(mac_address, user, db):
    logging.debug(f"Fetching data for MAC address: {mac_address}")
    base_path = f"grills/{mac_address}/grill"
    try:
        grill_temp = db.child(base_path).child("G4/4").get(user['idToken']).val()
        setpoint = db.child(base_path).child("G4/3").get(user['idToken']).val()
        
        run_status_code_raw = db.child(base_path).child("G4/1").get(user['idToken']).val()
        run_status_code = run_status_code_raw.strip() if isinstance(run_status_code_raw, str) else run_status_code_raw
        logging.debug(f"Run Status Code (Processed): '{run_status_code}' (Length: {len(str(run_status_code))})")

        timeStamp = db.child(base_path).child("timeStamp").get(user['idToken']).val()

        run_states = {
            "0": "OFF AND COOL",
            "1": "BURNING",
            "2": "SHUTDOWN"
        }

        run_status = run_states.get(run_status_code, "UNKNOWN")

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


class MyApp(QWidget):
    def __init__(self, mac_address, user, db):
        super().__init__()
        self.mac_address = mac_address
        self.user = user
        self.db = db
        self.initUI()
        self.loadMacAddresses()  # Load MAC addresses first

        # Add the command line MAC address to the list if not already present
        if self.mac_address and self.mac_address not in self.macAddresses:
            self.macAddresses.append(self.mac_address)
            self.macComboBox.addItem(self.mac_address)
            self.saveMacAddresses()  # Save the updated list

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
        self.loadMacAddresses()  # Load previously stored MAC addresses

        self.macSubmitButton = QPushButton('Connect', self)
        self.macSubmitButton.clicked.connect(self.submitMacAddress)
        self.layout.addWidget(self.macSubmitButton)
        
        self.quitButton = QPushButton('Quit', self)
        self.quitButton.clicked.connect(self.close)
        self.layout.addWidget(self.quitButton)

        self.setLayout(self.layout)
        self.setWindowTitle('Grill Monitor')
        self.show()

        # Update data every X milliseconds (e.g., 5000ms = 5 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateData)
        self.timer.start(5000)
    def onMacSelected(self, text):
        # Logic to handle connection to the selected MAC address
        self.mac_address = text
        self.titleLabel.setText(f"Monitoring device: {self.mac_address}")
        self.updateData()

    def submitMacAddress(self):
        mac_address = self.macInput.text().strip()
        if mac_address and self.isValidMacAddress(mac_address):
            if mac_address not in self.macAddresses:
                self.macAddresses.append(mac_address)
                self.macComboBox.addItem(mac_address)
                self.saveMacAddresses()
            
            # Update current MAC address and fetch details
            self.mac_address = mac_address
            self.titleLabel.setText(f"Monitoring device: {self.mac_address}")
            self.updateData()  # Fetch and update data for the new MAC address
        else:
            # Handle invalid MAC address format
            print("Invalid MAC address format.")

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
                self.macAddresses = json.load(file)
                self.macComboBox.clear()  # Clear existing items before adding new ones
                self.macComboBox.addItems(self.macAddresses)
        except FileNotFoundError:
            self.macAddresses = []


    def submitMacAddress(self):
        mac_address = self.macInput.text()
        if mac_address and mac_address not in self.macAddresses:
            self.macAddresses.append(mac_address)
            self.macComboBox.addItem(mac_address)
            with open('mac_addresses.json', 'w') as file:
                json.dump(self.macAddresses, file)
                
    def updateData(self):
        data = get_firebase_data(self.mac_address, self.user, self.db)
        
        # Check the run status and hide/show the labels accordingly
        run_status_code = data.get("Run Status")
        if run_status_code == "OFF AND COOL":
            self.grillTempLabel.hide()
            self.setpointLabel.hide()
        else:
            # Update with actual values and show the labels if the grill is not OFFANDCOOL
            grill_temp = data.get("Grill Temp", "Loading...")
            setpoint = data.get("Setpoint", "Loading...")
            self.grillTempLabel.setText(f"Grill Temp: {grill_temp}")
            self.setpointLabel.setText(f"Setpoint: {setpoint}")
            self.grillTempLabel.show()
            self.setpointLabel.show()

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
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
