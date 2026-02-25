import sys
import os 
import argparse
import time 

import subprocess
import multiprocessing as mp
from multiprocessing import Process, Value, Lock

from PIL import Image

etcpak_exefile_path = os.path.join(os.getcwd(), "encoders", "etcpak", "etcpak.exe")
astc_exefile_path = os.path.join(os.getcwd(), "encoders", "astcenc", "astcenc-avx2.exe")

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Texture Compression Batch Tool: Wrapper for Texture Compression",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 1. Common option group 
    common_group = parser.add_argument_group("Common Options")
    common_group.add_argument("-d", "--data_path", type=str, required=True, help="Input data image path")
    common_group.add_argument("-o", "--output_path", type=str, required=True, help="Compressed output save path")
    common_group.add_argument("-c", "--codec", type=str, required=True,
                              choices=["astc", "bc1", "bc3", "bc4", "bc5", "bc7", "etc1", "etc2"],
                              help="Select codec format")

    # 2. Performance & Concurrency Options 
    perf_group = parser.add_argument_group("Performance & Concurrency Options")
    perf_group.add_argument("-nP", "--nProcesses", type=int, default=1, help="Number of Python processes")
    perf_group.add_argument("-nT", "--nThreads", type=int, default=1, help="Number of threads per process")

    # 3. ETC2 Spcific Options 
    etc2_group = parser.add_argument_group("ETC2 Specific Options")
    etc2_group.add_argument("--etc2_hq", action="store_true", 
                            help="Enable High Quality mode (Valid only for etc2_rgb / etc2_rgba)")

    # 4. ASTC Specific Options 
    astc_group = parser.add_argument_group("ASTC Specific Options")
    # astc_group.add_argument("--astc_mode", type=str, choices=["l", "s", "h", "H"], default=argparse.SUPPRESS,
    #                         help="Mode: l(linear LDR), s(sRGB LDR), h(HDR RGB/LDR A), H(HDR)")
    
    astc_group.add_argument("--astc_quality", type=str, default="medium",
                            help="Quality: fastest/fast/medium/thorough/verythorough/exhaustive")
    
    astc_blocks = ["4x4", "5x4", "5x5", "6x5", "6x6", "8x5", "8x6", 
                   "3x3x3", "4x3x3", "4x4x3", "4x4x4", "5x4x4"]
    astc_group.add_argument("--astc_block_size", type=str, default="4x4", choices=astc_blocks, 
                            help="2D or 3D block size for ASTC")

    args = parser.parse_args()

    # Check if --etc2_hq is used with a non-ETC2 codec
    if args.codec not in ["etc2"] and args.etc2_hq:
        parser.error(f"The --etc2_hq option is only valid for 'etc2_rgb' or 'etc2_rgba' codecs. (Current codec: {args.codec})")

    # Check if ASTC-specific options are explicitly used with a non-ASTC codec
    if args.codec != "astc":
        # astc_mode is suppressed by default, so it only exists if explicitly provided
        if hasattr(args, 'astc_mode'):
            parser.error("The --astc_mode option is only valid for the 'astc' codec.")
        
        # Check if the user explicitly provided --astc_quality or --astc_block_size via command line
        if '--astc_quality' in sys.argv or '--astc_block_size' in sys.argv:
            print("[Warning] ASTC-specific options (--astc_quality, --astc_block_size) will be ignored since the chosen codec is not 'astc'.")

    return args

# Process Function
def works(args, images, image_index, lock):
    while True:
        with lock:
            index = image_index.value
            image_index.value += 1

        if index >= len(images):
            break
            
        input_path = images[index]
        filename = os.path.basename(input_path)
        name, _ = os.path.splitext(filename)
        rel_path = os.path.relpath(input_path, args.data_path)
        rel_dir = os.path.dirname(rel_path)
        
        if args.codec == "astc":
            output_path = os.path.join(args.output_path, "astc", rel_dir, name + ".astc")
            command = [
                astc_exefile_path, 
                "-cl", input_path, 
                output_path, 
                args.astc_block_size, 
                f"-{args.astc_quality}",  
                "-j", str(args.nThreads)
            ]
        else:
            # Checking alpha image
            img = Image.open(input_path)
            codec = args.codec 

            if args.codec == "etc2" and len(img.getbands()) == 4:
                codec = "etc2_rgba"
            else:
                codec = "etc2_rgb"

            output_path = os.path.join(args.output_path, "ktx", rel_dir, name + ".ktx")
            command = [
                etcpak_exefile_path, 
                "-M", 
                "-c", codec,
                "-t", str(args.nThreads),
                input_path, 
                output_path, 
            ]

            if args.etc2_hq:
                command.append("--etc2_hq")

            # if args.mipmaps:
            #     command.append("--mipmaps")

        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Error encoding {filename}: {e}")

if __name__ == "__main__":
    args = parse_arguments()

    os.makedirs(args.output_path, exist_ok=True)
    os.makedirs(os.path.join(args.output_path, "ktx"), exist_ok=True)
    os.makedirs(os.path.join(args.output_path, "png"), exist_ok=True)

    # ---------------------------------------------------------
    # WORK FLOW 2: Image Loading & Construct Output Folder Structure
    # ---------------------------------------------------------
    img_extensions = ('.jpg', '.jpeg', '.png','.bmp')
    image_paths = []

    for root, dirs, files in os.walk(args.data_path):
        rel_path = os.path.relpath(root, args.data_path)
        
        if args.codec == "astc":
            target_dir = os.path.join(args.output_path, "astc", rel_path)
        else:
            target_dir = os.path.join(args.output_path, "ktx", rel_path)

        decompressed_dir = os.path.join(args.output_path, "png", rel_path)
        os.makedirs(target_dir, exist_ok=True)
        os.makedirs(decompressed_dir, exist_ok=True)

        for file in files:
            if file.lower().endswith(img_extensions):
                image_paths.append(os.path.join(root, file))

    # ---------------------------------------------------------
    # WORK FLOW 3: Image Sorting by File Size
    # ---------------------------------------------------------
    image_paths.sort(key=lambda x: os.path.getsize(x), reverse=True)

    # ---------------------------------------------------------
    # DEBUG: Print Configuration
    # ---------------------------------------------------------
    # print("\n===  Configuration  ===")
    # print(f"OS Info       : {platform.system()} {platform.release()} ({platform.machine()})")
    # print(f"CPU info      : {platform.processor()}")
    # print(f"Available CPU : {mp.cpu_count()} cores")
    # print("-" * 25)
    # print(f"Input Path    : {args.data_path}")
    # print(f"Output Path   : {args.output_path}")
    # print(f"Codec         : {args.codec.upper()}")
    # print(f"Processes     : {args.nProcesses} / Threads per process: {args.nThreads}")
    # print(f"Total Images  : {len(image_paths)} files found.")
    # print("========================\n")

    if len(image_paths) == 0:
        print("Error: No images found in the target directory.")
        sys.exit(1)

    # ---------------------------------------------------------
    # WORK FLOW 4: Encoding Start (Multi-Processing)
    # ---------------------------------------------------------
    image_index = Value('i', 0)
    lock = Lock()
    processes = [Process(target=works, args=(args, image_paths, image_index, lock)) for _ in range(args.nProcesses)]
    
    program_start_time = time.perf_counter()

    for process in processes:
        process.start()
        
    for process in processes:
        process.join()

    program_end_time = time.perf_counter()
    print(f"{args.codec}, {(program_end_time - program_start_time) * 1000:.4f}")