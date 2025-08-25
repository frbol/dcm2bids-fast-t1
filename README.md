# dcm2bids-fast-t1
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.16941366.svg)](https://doi.org/10.5281/zenodo.16941366)

Fast DICOM → NIfTI converter for neuroimaging, selects best T1 (and optional FLAIR).


**minimal and fast** Python wrapper for [dcm2niix](https://github.com/rordenlab/dcm2niix) that automatically selects and converts **the single best T1-weighted MRI** (and optionally the best FLAIR) from a DICOM folder into NIfTI format.  
It scans DICOM headers quickly with [pydicom](https://github.com/pydicom/pydicom), finds the most relevant series, and calls `dcm2niix` only on that subset.

## Features
- Fast — scans headers instead of running `dcm2niix` on everything  
- Smart — picks the largest/highest-resolution T1 (and FLAIR if requested)  
- Simple — saves directly into a clean subject folder, no unnecessary subfolders  
- Flexible — works with single folders or in batch mode
  
## Citation

If you use this software in your research or publications, please cite:

**APA Style:**
> Loboda, F. (2025). dcm2bids-fast-t1 (Version 1.0.1) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.16941366
> 

**BibTeX:**
```bibtex
@software{Loboda2025_dcm2bids_fast_t1,
  author    = {Fr{\'e}d{\'e}ric Loboda},
  title     = {dcm2bids-fast-t1: A lightweight DICOM{\textrightarrow}NIfTI converter for T1/FLAIR MRI},
  year      = {2025},
  publisher = {Zenodo},
  version   = {1.0.1},
  doi       = {10.5281/zenodo.16941366},
  url       = {https://doi.org/10.5281/zenodo.16941366}
}
```


## Quickstart

```bash
python dcm2bids_fast_t1.py -i /path/to/DICOM/folder -o /path/to/output -s SUBJECT_ID
```

Optional: also convert the best FLAIR series

```bash
python dcm2bids_fast_t1.py -i /path/to/DICOM/folder -o /path/to/output -s SUBJECT_ID --with-flair
```

## Requirements

# core tool needed at system level
# macOS (Homebrew)
brew install dcm2niix
# or conda
conda install -c conda-forge dcm2niix

# python deps
pip install -r requirements.txt


## Usage

```bash
usage: dcm2bids_fast_t1.py [-h] [-i INPUT] [-o BIDS_ROOT] [-s SUBJECT]
                           [--session SESSION] [--with-flair] [--timeout TIMEOUT]
                           [--no-gzip] [--no-json] [--list]

FAST: convert only the best T1 (and optional FLAIR) series from a DICOM folder.

optional arguments:
  -h, --help            Show this help message and exit
  -i, --input           Input DICOM folder (recursive)
  -o, --bids-root       Output root folder
  -s, --subject         Subject label (e.g. 244S03_T3)
  --session             Session label (optional)
  --with-flair          Also convert the best FLAIR series
  --timeout             Timeout for dcm2niix (0 = no limit)
  --no-gzip             Write `.nii` instead of `.nii.gz`
  --no-json             Skip JSON sidecars
  --list                Only list candidate series without converting
```

## Examples

Convert one subject, keep only the best T1:

```bash
python dcm2bids_fast_t1.py -i ~/dicoms/244S03_T3 -o ~/BIDS_Project -s 244S03_T3
```

Convert and also include best FLAIR:

```bash
python dcm2bids_fast_t1.py -i ~/dicoms/244S03_T3 -o ~/BIDS_Project -s 244S03_T3 --with-flair
```

List all candidate series before deciding:

```bash
python dcm2bids_fast_t1.py -i ~/dicoms/244S03_T3 --list
