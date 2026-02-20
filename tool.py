import sys
import os 
import argparse
import time 

from multiprocessing import *
import multiprocessing as mp

# Data path
etcpak_exefile_path = os.getcwd() + "\\etcpak\\build\\Release\\etcpak"
data_path = os.getcwd() + "\\images\\"
result_path = os.getcwd() + "\\test\\"

# Process Function
def works(nThreads, images, image_index, lock):
    index = 0

    while True:
        with lock:
            index = image_index.value
            image_index.value += 1

        if (index >= len(images)): 
            break
        os.system(etcpak_exefile_path + " -M -c bc7 -n " + str(nThreads) + " " + data_path + images[index] + " " + result_path + os.path.splitext(images[index])[0] + ".ktx")
        # index += 1

if __name__ == "__main__":
    print(f"You can make process count = {mp.cpu_count()}")

    # Parser 
    parser = argparse.ArgumentParser(
        prog = "Trade-off Multiprocessing vs Multi-threading",
        description = "you have to write number of process and threads",
    )
    parser.add_argument("-nP", "--nProcesses", type=int, help="Number of Process", required=True)
    parser.add_argument("-nT", "--nThreads", type=int, help="Number of Process", required=True)

    args = parser.parse_args()
    
    # data load from data dir path
    images = os.listdir(data_path)

    # Shared memory for multi-processing 
    image_index = Value('i', 0) # image index to access image path array 
    lock = mp.Lock() # To solve data race condition

    # process count 
    num_of_process = args.nProcesses
    # define process 
    processes = [Process(target=works, args=(args.nThreads, images, image_index, lock)) for _ in range(num_of_process)] 

    # MAIN PROGRAM
    program_start_time = time.perf_counter();
    for process in processes:
        process.start()
    
    for process in processes:
        process.join()

    program_end_time = time.perf_counter();
    print(f"Done, Program time : {round((program_end_time - program_start_time) * 1000, 4)} ms")