# Texture Compression Wrapper v1.0

A high-performance multi-processing texture compression wrapper built on top of etcpak and astcenc.

This tool is designed for:

- Large-scale texture dataset compression
- Batch preprocessing pipelines
- Compression benchmarking experiments
- Multi-process + multi-threaded encoding workflows

The wrapper automatically analyzes image channel information and selects the proper compression format internally (e.g., BC1 vs BC3, ETC2 RGB vs RGBA).

---

# Features

- Fast multi-processing texture compression pipeline
- Automatic codec selection based on image channel count
- Supports:
  - BC1 / BC3 / BC4 / BC5 / BC7
  - ETC1 / ETC2
  - ASTC
- Automatic RGB / RGBA handling
- Folder structure preservation
- Dataset-scale batch processing
- ASTC quality presets
- ASTC PSNR-target encoding
- QuickBC7 heuristic toggle support
- ETC2 High Quality mode support

---

# Supported Compression Formats

| User Option | Actual Output Codec |
|---|---|
| `bc1_bc3` | BC1 (RGB) / BC3 (RGBA) |
| `bc4` | BC4 |
| `bc5` | BC5 |
| `bc7` | BC7 |
| `etc1` | ETC1 |
| `etc2` | ETC2 RGB / ETC2 RGBA |
| `etc2_r` | ETC2 R11 |
| `etc2_rg` | ETC2 RG11 |
| `astc` | ASTC |

---

# Installation

## 1. Clone Repository

```powershell
git clone --recursive https://github.com/gusrlLee/texture_compression_tool.git
cd texture_compression_tool
```

---

## 2. Build Encoder Dependencies

```powershell
./install_window.bat
```

This script automatically:

- Builds `etcpak`
- Downloads/builds `astcenc`
- Creates the required encoder directory structure

---

# Python Dependencies

## Requirements

```text
Python >= 3.7
Pillow
```

## Install Pillow

```powershell
pip install pillow
```

---

# Project Structure

After installation, the project structure should look like:

```text
project_root/
│
├── encoders/
│   ├── etcpak/
│   │   └── etcpak.exe
│   │
│   ├── astcenc/
│   │   └── astcenc-avx2.exe
│   │
│   └── astcenc-psnr/
│       └── astcenc-avx2.exe
│
├── tool.py
└── README.md
```

---

# Supported Input Formats

The tool recursively scans the dataset directory for:

```text
.png
.jpg
.jpeg
.bmp
```

---

# Quick Start

## Basic Usage
Compress a dataset using BC7 compression:

```powershell
python tool.py 
--codec bc7 
--data_path ./dataset 
--output_path ./compressed_output
```

The tool will:

1. Scan the dataset recursively
2. Detect image channel counts automatically
3. Compress textures
4. Preserve the original folder hierarchy
5. Save outputs into the output directory

---

# Command Line Arguments

## Common Options

| Argument | Type | Default | Description |
|---|---|---|---|
| `-c`, `--codec` | `str` | Required | Compression codec |
| `-m`, `--mode` | `int` | `2` | Sorting mode (`0`: Random, `1`: Ascending Size, `2`: Descending Size) |
| `-d`, `--data_path` | `str` | Required | Input texture dataset directory |
| `-o`, `--output_path` | `str` | Required | Output directory |

---

## Performance & Concurrency Options

| Argument | Type | Default | Description |
|---|---|---|---|
| `-nP`, `--nProcesses` | `int` | `1` | Number of worker processes |
| `-nT`, `--nThreads` | `int` | `12` | Number of threads passed to encoder |

---

## BC7 Options

| Argument | Type | Default | Description |
|---|---|---|---|
| `--disable_heuristics` | `flag` | `False` | Disable QuickBC7 heuristics |

---

## ETC2 Options

| Argument | Type | Default | Description |
|---|---|---|---|
| `--etc2_hq` | `flag` | `False` | Enable ETC2 High Quality mode |

---

## ASTC Options

| Argument | Type | Default | Description |
|---|---|---|---|
| `--astc_mode` | `str` | `cl` | ASTC color mode (`cl`, `cs`, `ch`, `cH`) |
| `--astc_quality` | `str` | `medium` | Compression quality preset |
| `--astc_block_size` | `str` | `4x4` | ASTC block size |
| `--target_psnr` | `int` | `None` | Target PSNR value (disabled if not specified) |

---

# Supported Codec Values

| Codec | Description |
|---|---|
| `astc` | ASTC compression |
| `bc1_bc3` | Automatic BC1 / BC3 selection |
| `bc4` | BC4 compression |
| `bc5` | BC5 compression |
| `bc7` | BC7 compression |
| `etc1` | ETC1 compression |
| `etc2_r` | ETC2 single-channel compression |
| `etc2_rg` | ETC2 dual-channel compression |
| `etc2` | Automatic ETC2 RGB / RGBA selection |

---

# Automatic Channel-Aware Compression

The wrapper automatically selects appropriate formats based on texture channel count.

| Input Channels | Selected Codec |
|---|---|
| 1 Channel | BC4 / ETC2_R |
| 2 Channels | BC5 / ETC2_RG |
| 3 Channels | BC1 / ETC2_RGB |
| 4 Channels | BC3 / ETC2_RGBA |

This simplifies large-scale dataset preprocessing workflows.

---

# Output Structure

The original dataset directory structure is preserved automatically.

## Input Dataset

```text
dataset/
├── character/
│   └── albedo.png
└── terrain/
    └── rock.png
```

## BC / ETC Output

```text
output/
├── ktx/
│   ├── character/
│   │   └── albedo.ktx
│   └── terrain/
│       └── rock.ktx
```

## ASTC Output

```text
output/
└── astc/
    ├── character/
    │   └── albedo.astc
    └── terrain/
        └── rock.astc
```

---

# Examples

## BC7 Compression

```powershell
# Compress dataset using BC7
# 4 worker processes
# 6 threads per encoder process

python tool.py 
--codec bc7 
--disable_heuristics 
--data_path ./my_texture_dataset 
--output_path ./compressed_output 
--nProcesses 4 
--nThreads 6
```

---

## ETC2 Compression

```powershell
# Compress dataset using ETC2 High Quality mode

python tool.py 
--codec etc2 
--etc2_hq 
--data_path ./my_texture_dataset 
--output_path ./compressed_output 
--nProcesses 4 
--nThreads 6
```

---

## ASTC Compression

```powershell
# Compress dataset using ASTC
# Medium quality
# 4x4 block size
# Target PSNR = 50

python tool.py 
--codec astc
--astc_quality medium 
--astc_block_size 4x4 
--target_psnr 50 
--data_path ./my_texture_dataset 
--output_path ./compressed_output 
--nProcesses 6 
--nThreads 4
```

---

## License
- [etcpak 2.1](https://github.com/wolfpld/etcpak): BSD 3-Clause
- [astc-encoder](https://github.com/ARM-software/astc-encoder): Apache 2.0
