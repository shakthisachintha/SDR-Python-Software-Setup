import h5py
import threading
import numpy as np
import os


def getData(cfileName):
    """
    Given a name of a *.cfile, this function extracts the interleaved
    Inphase-Quadrature data samples and convert it into a numpy array of complex
    data elements. *.cfile format has interleaved I and Q samples where each sample
    is a float32 type. GNURadio Companion (GRC) scripts output data into a file
    though a file sink block in this format.
    Read more in SDR data types: https://github.com/miek/inspectrum
    """
    # Read the *.cfile which has each element in float32 format.
    data = np.fromfile(cfileName, np.float32)
    # Take each consecutive interleaved I sample and Q sample to create a single complex element.
    data = data[0::2] + 1j*data[1::2]

    # print("data type=", type(data))

    # Return the complex numpy array.
    return data


pattern_names = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5']
compression_rate = 5

file_threads = []


def compressDelete(freq, group):
    # frequecy for determining the folder
    # group for add files
    global file_threads
    for pattern in pattern_names:
        thread = threading.Thread(target=create_datasets, args=(
            group, compression_rate, pattern, freq))
        file_threads.append(thread)


def create_datasets(group, compression_rate, pattern, freq):

    # For IQ File
    file_name = f"./Data/{freq}MHZ/{pattern}_{freq}MHZ.iq"
    print("Compressing File: ", file_name)
    data = getData(file_name)
    group.create_dataset(f'{pattern}_IQ', data=data,
                         compression='gzip', compression_opts=compression_rate)

    print("Deleting File: ", file_name)
    os.remove(file_name)


freq_start = 66
freq_end = 75
comp_file = h5py.File('./Data/compressed.h5', 'w')
threads = []

for freq in range(freq_start, freq_end+1):
    group_name = f"{freq}MHZ"
    print("Creating Group: ", group_name)
    group = comp_file.create_group(group_name)
    # group = comp_file.get(group_name)
    thread = threading.Thread(target=compressDelete, args=(freq, group,))
    threads.append(thread)

#Starting Threads
print("Creating threads")
for each in threads:
    each.start()

# Waiting for finish the job
print("Waiting for all threads")
for each in threads:
    each.join()

for each in file_threads:
    each.start()

for each in file_threads:
    each.join()

comp_file.close()
