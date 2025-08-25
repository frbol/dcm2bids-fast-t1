# dcm2bids-fast-t1
Fast DICOM → NIfTI converter for neuroimaging, selects best T1 (and optional FLAIR).


 **minimal and fast** Python wrapper for [dcm2niix](https://github.com/rordenlab/dcm2niix) that automatically selects and converts **the single best T1-weighted MRI** (and optionally the best FLAIR) from a DICOM folder into NIfTI format.  
It scans DICOM headers quickly with [pydicom](https://github.com/pydicom/pydicom), finds the most relevant series, and calls `dcm2niix` only on that subset.

## Features
- Fast — scans headers instead of running `dcm2niix` on everything  
- Smart — picks the largest/highest-resolution T1 (and FLAIR if requested)  
- Simple — saves directly into a clean subject folder, no unnecessary subfolders  
- Flexible — works with single folders or in batch mode  

## Requirements
- [dcm2niix](https://github.com/rordenlab/dcm2niix) in your PATH  
  - macOS: `brew install dcm2niix`  
  - Conda: `conda install -c conda-forge dcm2niix`  
- Python packages:
  ```bash
  pip install pydicom
