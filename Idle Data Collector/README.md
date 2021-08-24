# Data Collection Script HackRF-Python-Scapy-GNURadio

## Instructions
1. Install GNU Radio Companion with Osomosdr
2. Install Scapy
3. Install other necessary python libraries
4. By using Scapy, have to find the relevant network interface to sniff
    - Run command `sudo scapy` in terminal to run scapy in super user mode
    - On Scapy command window run `IFACES` to get details about network interfaces
    - There you can find the appropriate interface and edit it on the config file
5. Run the script in python3.7 or any suitable version (python3.7 is recommended)
    - Run as super user `sudo python3.7 script.py`<br>
      This will run for the mentioned frequency range and will create output files in Data folder
