#!/usr/bin/env Python3

# region Library Imports
import configparser
import os
import time
import threading
import osmosdr
from gnuradio import blocks
from gnuradio import analog
from gnuradio import audio
from gnuradio import gr
from scapy.all import *
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
# endregion


# region Config Parsing
config = configparser.ConfigParser()
config.read('config.ini')
general_config = config['GENERAL']
hardware_config = config['HACKRF.HARDWARE']
sender_config = config['PACKET.SENDER']
sniffer_config = config['PACKET.SNIFFER']

freq_multiplier = float(general_config['FreqMultiplier'])
start_freq = int(general_config['FreqRangStart'])
end_freq = int(general_config['FreqRangeEnd'])
step = int(general_config['Step'])
out_folder = general_config['OutputFolderPath']

sample_rate = float(hardware_config['SampleRate']) * 1e06
bb_gain = float(hardware_config['BbGain'])
if_gain = float(hardware_config['IfGain'])
rf_gain = float(hardware_config['RfGain'])
agc = bool(True if hardware_config['GainControl'] == 'True' else False)

packet_burst_count = int(sender_config['BurstSize'])
packet_destination = sender_config['PacketDestination']
packet_stop_destination = sender_config['StopDestionation'] 

sniffer_interface = sniffer_config['Interface']
# endregion


# region Create Output Directory
if not os.path.isdir(out_folder):
    os.mkdir(out_folder)
# endregion


# region GNU Radio Top Block Class
class my_top_block(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self)

        # Osmocom Source
        self.osmosdr_source_0 = osmosdr.source(
            args="numchan=" + str(1) + " " + ''
        )
        self.osmosdr_source_0.set_time_unknown_pps(osmosdr.time_spec_t())
        self.osmosdr_source_0.set_sample_rate(sample_rate)
        self.osmosdr_source_0.set_freq_corr(0, 0)
        self.osmosdr_source_0.set_dc_offset_mode(0, 0)
        self.osmosdr_source_0.set_iq_balance_mode(0, 0)
        self.osmosdr_source_0.set_gain_mode(agc, 0)
        self.osmosdr_source_0.set_gain(rf_gain, 0)
        self.osmosdr_source_0.set_if_gain(if_gain, 0)
        self.osmosdr_source_0.set_bb_gain(bb_gain, 0)
        self.osmosdr_source_0.set_antenna('', 0)
        self.osmosdr_source_0.set_bandwidth(0, 0)

# endregion


# region Top Block Functions
tb = my_top_block()


def run_tb():
    print(f"Frequency: {tb.osmosdr_source_0.get_center_freq()/1e6} Mhz")
    print("\tHackRf Ready")
    evt_hackrf_ready.set()
    evt_start_data_collection.wait()
    evt_data_collection_started.set()
    print("\tHackRf Collecting data")
    tb.run()

def stop_tb():
    print("\tHackRF stopping")
    tb.stop()
    tb.blocks_file_sink_0.close()
    print("\tHackRF file sink closed")
    time.sleep(2)
    print("\tHackRF stopped")

# endregion


# region Fresh Start
def fresh_start(freq):
    freq = f"{freq}MHZ"
    folder_name = f"./Data/{freq}"
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)
    path = f"{folder_name}/"
    file_name = f"{path}{freq}.iq"
    open(file_name, "w").close()
    return (file_name, path)
# endregion


# region Packets Sender
def sendPackets(count=100):
    payload = 'PAYLOAD'
    for i in range(2):
        payload = payload + payload

    ip_packet = IP(dst=packet_destination) / Raw(load=payload)

    # wait to start packet sending
    print("\tSender: Waiting for sniffer")
    evt_sniffer_ready.wait()
    evt_start_data_collection.set()
    print("\tSender: Start data collection")
    evt_data_collection_started.wait()
    time.sleep(0.5)
    print("\tPacket sending started")
    # Send packets
    send(ip_packet, count=count, verbose=False)

    # This packet commands to stop the sniffing
    send((IP(dst=packet_stop_destination) / TCP() / Raw(load=payload)), verbose=False)
    print("\tPackets sent")
# endregion


# region Sniffer Functions
def stopfilter(x):
    if x[IP].dst == packet_stop_destination:
        return True
    else:
        return False


def packetFilter(x):
    # Filter only sending packets and only IP packets
    return x[Ether].src == Ether().src and x[Ether].type == 2048


def sniffPackets(freq, pcap_path):
    print("\tSniffer: Waiting for hackrf")
    evt_hackrf_ready.wait()
    evt_sniffer_ready.set()
    evt_data_collection_started.wait()

    print("\tSniffing started...")
    pckts = sniff(iface=sniffer_interface, lfilter=packetFilter, stop_filter=stopfilter)

    time.sleep(0.5)
    evt_stop_data_collection.set()
    stop_tb()

    print("\tSniffing stopped...")
    wrpcap(f'{pcap_path}/{freq}Mhz_sniffed.pcap', pckts)
    print("\tPcap file saved...")
# endregion


# region Main Thread
def main():
    for freq in range(start_freq, end_freq+1, step):
        tb.osmosdr_source_0.set_center_freq(freq * 1e6)
        file_sink_name, path = fresh_start(freq)
        tb.blocks_file_sink_0 = blocks.file_sink(
            gr.sizeof_gr_complex*1, file_sink_name, False)
        tb.blocks_file_sink_0.set_unbuffered(False)
        tb.disconnect_all()
        tb.connect((tb.osmosdr_source_0, 0), (tb.blocks_file_sink_0, 0))

        thread_top_block = threading.Thread(target=run_tb)
        thread_sniffer = threading.Thread(target=sniffPackets, args=(freq,path,))
        thread_sender = threading.Thread(target=sendPackets, args=(packet_burst_count,))
        
        thread_sender.start()
        thread_sniffer.start()
        thread_top_block.start()

        thread_sender.join()
        thread_sniffer.join()
        thread_top_block.join()

        evt_hackrf_ready.clear()
        evt_sniffer_ready.clear()
        evt_start_data_collection.clear()
        evt_data_collection_started.clear()
        evt_stop_data_collection.clear()

# endregion


if __name__ == '__main__':
    evt_hackrf_ready = threading.Event()
    evt_sniffer_ready = threading.Event()
    evt_start_data_collection = threading.Event()
    evt_data_collection_started = threading.Event()
    evt_stop_data_collection = threading.Event()
    main()
