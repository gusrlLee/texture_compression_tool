import sys
import os 
import argparse
import time 
import platform

import subprocess
import multiprocessing as mp
from multiprocessing import Process, Value, Lock

etcpak_exefile_path = os.path.join(os.getcwd(), "encoders", "etcpak", "etcpak.exe")
astc_exefile_path = os.path.join(os.getcwd(), "encoders", "astcenc", "astcenc-native")

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
                "-cl", input_path, output_path, args.block_size,
                f"-{args.quality}", 
                "-j", str(args.nThreads)
            ]
        else:
            # 3. 폴더 구조를 완벽하게 유지한 최종 출력 경로 조립!
            output_path = os.path.join(args.output_path, "ktx", rel_dir, name + ".ktx")
            
            # 4. subprocess에 맞게 커맨드라인 분리 (매우 중요)
            command = [
                etcpak_exefile_path, 
                "-M", 
                "-c", args.codec,          # 띄어쓰기 대신 리스트 요소로 분리!
                "-t", str(args.nThreads),  # args.nThreads는 숫자이므로 문자열(str)로 변환
                input_path, 
                output_path, 
            ]
            if args.mipmaps:
                command.append("--mipmaps")

        # 명령어 실행 (subprocess 활용)
        # print(f"[Process-{os.getpid()}] Encoding: {filename} -> {os.path.basename(output_path)}")
        try:
            # shell=False로 안전하게 실행, 출력이 겹치지 않게 stdout 숨김 처리 (필요시 제거)
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Error encoding {filename}: {e}")

if __name__ == "__main__":
# Parser 
    parser = argparse.ArgumentParser(
        description="Texture Compression Batch Tool: Wrapper for astcenc & etcpak",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    common_group = parser.add_argument_group("Common Options")
    common_group.add_argument("-d", "--data_path", type=str, required=True, help="Input data image path")
    common_group.add_argument("-o", "--output_path", type=str, required=True, help="Compressed output save path")
    common_group.add_argument("-c", "--codec", type=str, required=True,
                              choices=["astc", "bc1", "bc3", "bc4", "bc5", "bc7", "etc1", "etc2_rgb", "etc2_rgba"],
                              help="Select codec format")

    perf_group = parser.add_argument_group("Performance & Concurrency Options")
    perf_group.add_argument("-nP", "--nProcesses", type=int, default=1, help="Number of Python processes")
    perf_group.add_argument("-nT", "--nThreads", type=int, default=1, help="Number of threads per process")

    encoder_group = parser.add_argument_group("Encoder Specific Options")
    encoder_group.add_argument("-q", "--quality", type=str, default="medium",
                               choices=["fast", "medium", "thorough", "exhaustive"], help="Compression quality")
    
    encoder_group.add_argument("-b", "--block_size", type=str, default="4x4", help="ASTC block size")
    encoder_group.add_argument("--mipmaps", action="store_true", help="Generate mipmaps")

    args = parser.parse_args()

    # 출력 폴더 생성
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
    # WORK FLOW 1: Print Configuration
    # ---------------------------------------------------------
    print("\n===  Configuration  ===")
    print(f"OS Info       : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"CPU info      : {platform.processor()}")
    print(f"Available CPU : {mp.cpu_count()} cores")
    print("-" * 25)
    print(f"Input Path    : {args.data_path}")
    print(f"Output Path   : {args.output_path}")
    print(f"Codec         : {args.codec.upper()}")
    print(f"Processes     : {args.nProcesses} / Threads per process: {args.nThreads}")
    print(f"Total Images  : {len(image_paths)} files found.")
    print("========================\n")

    if len(image_paths) == 0:
        print("Error: No images found in the target directory.")
        sys.exit(1)

    # ---------------------------------------------------------
    # WORK FLOW 4: Encoding Start (Multi-Processing)
    # ---------------------------------------------------------
    print("===  Encoding Start  ===")
    image_index = Value('i', 0)
    lock = Lock()
    processes = [Process(target=works, args=(args, image_paths, image_index, lock)) for _ in range(args.nProcesses)]
    
    program_start_time = time.perf_counter()

    for process in processes:
        process.start()
        
    for process in processes:
        process.join()

    program_end_time = time.perf_counter()
    
    print(f"\n[Done] All tasks completed.")
    print(f"Total Elapsed Time: {(program_end_time - program_start_time) * 1000:.2f} ms")