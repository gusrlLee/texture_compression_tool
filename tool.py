"""
Texture Compression Wrapper Tool V 1.0
================================
A multi-processing wrapper script for rapidly compressing large datasets
of image textures using etcpak and astcenc encoders
"""

import sys
import os 
import argparse
import time 
import random
from dataclasses import dataclass 
import subprocess
import multiprocessing as mp
from multiprocessing import Process, Value, Lock

from PIL import Image

random.seed(42)

# ---------------------------------------------------------
# GLOBAL CONFIGURATION (Encoder Executable Paths)
# ---------------------------------------------------------
ENCODERS_DIR = os.path.join(os.getcwd(), "encoders")
ETCPAK_EXE_FILE = os.path.join(ENCODERS_DIR, "etcpak", "etcpak.exe")
ASTCENC_EXE_FILE = os.path.join(ENCODERS_DIR, "astcenc", "astcenc-avx2.exe")
ASTCENC_PSNR_EXE_FILE = os.path.join(ENCODERS_DIR, "astcenc-psnr", "astcenc-avx2.exe")

@dataclass
class TextureInfo:
    path: str = None
    channel: int = None
    size: int = None

def parse_arguments():
    """
    Parses command-line arguments and validates user input logic.
    """
    parser = argparse.ArgumentParser(
        description="Texture Compression Batch Tool: Wrapper for Texture Compression",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 1. Common Options
    common_group = parser.add_argument_group("Common Options")
    common_group.add_argument("-c", "--codec", type=str, required=True,
                              choices=["astc", "bc1_bc3", "bc4", "bc5", "bc7", "etc1", "etc2_r", "etc2_rg", "etc2"],
                              help="Compression format for encoding textures.")
    common_group.add_argument("-m", "--mode", type=int, default=2, help="Sorting mode (0: Random, 1: Ascending Size, 2: Descending Size).")
    common_group.add_argument("-d", "--data_path", type=str, required=True, help="Directory path of input images.")
    common_group.add_argument("-o", "--output_path", type=str, required=True, help="Output directory path for compressed files.")

    # 2. Performance & Concurrency Options
    perf_group = parser.add_argument_group("Performance & Concurrency Options")
    perf_group.add_argument("-nP", "--nProcesses", type=int, default=1, help="Number of processes.")
    perf_group.add_argument("-nT", "--nThreads", type=int, default=1, help="Number of threads per process (passed to the encoder).")

    # 3. ETC2 Specific Options 
    etc2_group = parser.add_argument_group("ETC2 Specific Options")
    etc2_group.add_argument("--etc2_hq", action="store_true", 
                            help="Enable High Quality mode for ETC2 (Valid only for etc2_rgb / etc2_rgba).")

    # 4. ASTC Specific Options
    astc_group = parser.add_argument_group("ASTC Specific Options")
    astc_group.add_argument("--astc_mode", type=str, choices=["cl", "cs", "ch", "cH"], default="cl",
                            help="Color space mode: l(linear LDR), s(sRGB LDR), h(HDR RGB/LDR A), H(HDR).")
    
    astc_group.add_argument("--astc_quality", type=str, default="medium",
                            help="Compression quality preset: fastest/fast/medium/thorough/verythorough/exhaustive")
    
    astc_blocks = ["4x4", "5x4", "5x5", "6x5", "6x6", "8x5", "8x6", 
                   "3x3x3", "4x3x3", "4x4x3", "4x4x4", "5x4x4"]
    
    astc_group.add_argument("--astc_block_size", type=str, default="4x4", choices=astc_blocks, 
                            help="2D or 3D block size for ASTC.")
    
    astc_group.add_argument("--target_psnr", type=int, default=40, help="Target PSNR value (triggers astcenc-psnr executable).")

    # ---------------------------------------------------------
    # Validation Logic: Prevent conflicting arguments
    # ---------------------------------------------------------
    args = parser.parse_args()
    is_astc_opt_missing = not all(opt in sys.argv for opt in ['--astc_quality', '--astc_block_size'])

    if args.codec in ["bc1_bc3", "bc4", "bc5", "bc7"]:
        if args.etc2_hq:
            parser.error(f"[ERROR] The --etc2_hq option cannot be used with BC codecs (Current: {args.codec}).")
        if args.codec in ["bc4", "bc5"]:
            print(f"[INFO] 1-channel or 2-channel encoding selected (Current codec: {args.codec}).")

    if args.codec in ["etc1", "etc2_r", "etc2_rg", "etc2"]:
        if args.etc2_hq: 
            print("[INFO] High Quality mode requires AVX2 SIMD intrinsics.")
        if args.codec in ["etc2_r", "etc2_rg"]:
            print(f"[INFO] 1-channel or 2-channel encoding selected (Current codec: {args.codec}).")

    # General Cross-Checks
    if args.codec != "astc" and is_astc_opt_missing:
        print(f"[WARNING] ASTC-specific options will be ignored because the chosen codec is '{args.codec}'.")

    if args.codec == "astc":
        if args.etc2_hq:
            parser.error(f"[ERROR] The --etc2_hq option cannot be used with BC codecs (Current: {args.codec}).")
        if is_astc_opt_missing:
            print("[SYSTEM] Recommending ASTC specific configuration.")
        
    return args

def prepare_commands(args, image_infos):
    """
    Pre-assembles the CLI commands for texture compression based on image properties.
    
    This function iterates through the provided image metadata and dynamically 
    determines the appropriate encoder (etcpak or astcenc) and codec variant. 
    It adjusts the target codec based on the image's actual channel count 
    (e.g., using bc4/etc2_r for 1-channel, or selecting RGB/RGBA variants).
    
    Args:
        args (argparse.Namespace): The parsed command-line arguments.
        image_infos (list): A list of TextureInfo objects containing image metadata.
        
    Returns:
        list: A list of tuples, where each tuple contains (filename, command_list) 
              ready to be executed by the worker processes.
    """
    commands = []

    for info in image_infos:
        input_path = info.path
        file_name = os.path.basename(input_path)
        name, _ = os.path.splitext(file_name)
        rel_path = os.path.relpath(input_path, args.data_path)
        rel_dir = os.path.dirname(rel_path)

        # ---------------------------------------------------------
        # BC Codec Family
        # ---------------------------------------------------------
        if args.codec in ["bc1_bc3", "bc4", "bc5", "bc7"]:
            encoder = ETCPAK_EXE_FILE

            # Dynamically assign BC codec based on channel count
            if info.channel == 1:
                encoding_codec = "bc4"
            elif info.channel == 2:
                encoding_codec = "bc5"
            else:
                if args.codec == "bc7":
                    encoding_codec = "bc7"
                else:
                    has_alpha = (info.channel == 4)
                    encoding_codec = "bc3" if has_alpha else "bc1"

            # Define output path for KTX files
            output_path = os.path.join(args.output_path, "ktx", rel_dir, f"{name}.ktx")
            command = [
                encoder,
                "-M",
                "-c", encoding_codec,
                "-t", str(args.nThreads),
                input_path,
                output_path
            ]
            commands.append(command)

        # ---------------------------------------------------------
        # ETC Codec Family
        # ---------------------------------------------------------
        if args.codec in ["etc1", "etc2_r", "etc2_rg", "etc2"]:
            encoder = ETCPAK_EXE_FILE
            if info.channel == 1:
                encoding_codec = "etc2_r"
            elif info.channel == 2:
                encoding_codec = "etc2_rg"
            else:
                if args.codec == "etc1":
                    encoding_codec = "etc1"
                else:
                    has_alpha = (info.channel == 4)
                    encoding_codec = "etc2_rgba" if has_alpha else "etc2_rgb"

            output_path = os.path.join(args.output_path, "ktx", rel_dir, f"{name}.ktx")
            command = [
                encoder,
                "-M",
                "-c", encoding_codec,
                "-t", str(args.nThreads),
                input_path,
                output_path
            ]

            if args.etc2_hq and args.codec == "etc2":
                command.append("--etc2_hq")

            commands.append(command)

        # ---------------------------------------------------------
        # ASTC Codec
        # ---------------------------------------------------------
        if args.codec == "astc":
            is_psnr_active = 'target_psnr' in sys.argv
            encoder_exe = ASTCENC_PSNR_EXE_FILE if is_psnr_active else ASTCENC_EXE_FILE

            output_path = os.path.join(args.output_path, "astc", rel_dir, f"{name}.astc")
            command = [
                encoder_exe,
                f"-{args.astc_mode}",
                input_path,
                output_path,
                args.astc_block_size,
                f"-{args.astc_quality}",  
                "-j", str(args.nThreads)
            ]

            if is_psnr_active:
                command.append("-dbtarget", str(args.target_psnr))

            commands.append(command)

    return commands


def encoding(commands, index, lock):
    """
    Worker function for multiprocessing that executes the pre-assembled commands.
    
    This function safely fetches a task from the shared command list using a 
    multiprocessing lock, runs the command via subprocess, and suppresses 
    the standard output. If an error occurs during execution, it prints 
    an error message identifying the failed file.
    
    Args:
        commands (list): The list of pre-assembled command tuples (filename, command_list).
        index (multiprocessing.Value): A shared integer tracking the current task index.
        lock (multiprocessing.Lock): A lock to ensure thread-safe increments of the index.
    """
    while True:
        # Safely acquire the next index
        with lock:
            idx = index.value
            index.value += 1

        # Exit loop if all tasks are completed
        if idx >= len(commands):
            break
            
        command = commands[idx]

        try:
            # Execute the encoder command
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Error encoding : {e}")

if __name__ == "__main__":
    # get user input
    args = parse_arguments()

    # ---------------------------------------------------------
    # WORKFLOW 1: Construct Output Folder Structure
    # ---------------------------------------------------------
    img_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    image_paths = []

    # Pre-create base directories
    os.makedirs(args.output_path, exist_ok=True)

    if args.codec == "astc":
        os.makedirs(os.path.join(args.output_path, "astc"), exist_ok=True)
    else:
        os.makedirs(os.path.join(args.output_path, "ktx"), exist_ok=True)

    for root, dirs, files in os.walk(args.data_path):
        rel_path = os.path.relpath(root, args.data_path)
        target_dir = os.path.join(args.output_path, "astc" if args.codec == "astc" else "ktx", rel_path)
        
        os.makedirs(target_dir, exist_ok=True)

        for file in files:
            if file.lower().endswith(img_extensions):
                image_paths.append(os.path.join(root, file))
    
    if not image_paths:
        sys.exit("[ERROR] No valid images found in the target directory. Please check your data_path!")
    
    # ---------------------------------------------------------
    # WORKFLOW 2: Input Image Pre-processing and Sorting
    # ---------------------------------------------------------
    image_infos = []
    for image_path in image_paths:
        info = TextureInfo()
        info.path = image_path
        info.size = os.path.getsize(image_path)
        with Image.open(image_path) as img:
            info.channel = len(img.getbands())
        image_infos.append(info)

    if args.mode == 0:
        random.shuffle(image_infos)
    elif args.mode == 1:
        image_infos.sort(key=lambda info: info.size)
    else: # args.mode == 2
        image_infos.sort(key=lambda info: info.size, reverse=True)


    # ---------------------------------------------------------
    # WORKFLOW 3: Generate command for encoding
    # ---------------------------------------------------------
    commands = prepare_commands(args, image_infos)

    # ---------------------------------------------------------
    # WORK FLOW 4: Encoding Start (Multi-Processing)
    # ---------------------------------------------------------
    image_index = Value('i', 0)
    lock = Lock()
    processes = [Process(target=encoding, args=(commands, image_index, lock)) for _ in range(args.nProcesses)]
    
    program_start_time = time.perf_counter()

    for process in processes:
        process.start()
        
    for process in processes:
        process.join()

    program_end_time = time.perf_counter()

    # for expriment
    if args.codec == "etc1":
        print(f"{args.mode}, {args.codec}, {args.astc_mode}, {args.astc_block_size}, {args.astc_quality}, {args.target_psnr}, {args.etc2_hq}, {args.nProcesses}, {args.nThreads}, {(program_end_time - program_start_time) * 1000:.4f}")
    elif args.codec == "etc2":
        print(f"{args.mode}, {args.codec}, {args.astc_mode}, {args.astc_block_size}, {args.astc_quality}, {args.target_psnr}, {args.etc2_hq}, {args.nProcesses}, {args.nThreads}, {(program_end_time - program_start_time) * 1000:.4f}")
    elif args.codec == "astc":
        print(f"{args.mode}, {args.codec}, {args.astc_mode}, {args.astc_block_size}, {args.astc_quality}, {args.target_psnr}, {args.etc2_hq}, {args.nProcesses}, {args.nThreads}, {(program_end_time - program_start_time) * 1000:.4f}")
    else: # bc
        print(f"{args.mode}, {args.codec}, {args.astc_mode}, {args.astc_block_size}, {args.astc_quality}, {args.target_psnr}, {args.etc2_hq}, {args.nProcesses}, {args.nThreads}, {(program_end_time - program_start_time) * 1000:.4f}")
