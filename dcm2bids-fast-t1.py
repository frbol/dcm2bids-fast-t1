#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dcm2bids_fast_t1.py — FAST: convert ONLY the single best T1 (and optional FLAIR)
by pre-scanning DICOM headers, then running dcm2niix ONLY on the selected series.

Requirements:
  - dcm2niix in PATH (brew install dcm2niix | conda install -c conda-forge dcm2niix)
  - pydicom (pip install pydicom)
"""

import os, sys, re, shutil, time, argparse, subprocess, tempfile
from typing import Dict, List, Optional, Iterable, Tuple

# ---- EDIT DEFAULTS IF NEEDED ----
DEFAULT_INPUT     = "/Users/USERNAME/Downloads/DICOM_IN"
DEFAULT_BIDS_ROOT = "/Users/USERNAME/Downloads/NIFTI_OUT"
DEFAULT_SUBJECT   = "Subject01_converted"
DEFAULT_SESSION   = None
# ---------------------------------

# ---------- utils ----------
def which(prog: str) -> Optional[str]:
    from shutil import which as _w; return _w(prog)

def need_tools():
    if not which("dcm2niix"):
        sys.exit("❌ dcm2niix not found. Install with Homebrew: brew install dcm2niix")
    try:
        import pydicom  # noqa
    except Exception:
        sys.exit("❌ Missing pydicom. Install: pip install pydicom")

def stream_run(cmd: List[str], timeout_s: int = 0) -> int:
    start = time.time()
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, bufsize=1, universal_newlines=True) as p:
        try:
            for line in p.stdout:
                if line:
                    sys.stdout.write(line); sys.stdout.flush()
                if timeout_s and (time.time()-start) > timeout_s:
                    p.kill(); raise TimeoutError("Process timed out")
        except KeyboardInterrupt:
            p.kill(); raise
        return p.wait()

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

# ---------- header scan ----------
RX_DROP = re.compile(r"(?i)(localizer|scout|survey|autoalign|ASSET|ARC|MOCO|MOTION|DERIVED|SECONDARY|NOISE|CALIB|B1|ND|GRAPPA|SENSE|CLEAR|TEST)")

def safe_float(x):
    try: return float(x)
    except: return None

def walk_dicoms(root: str) -> Iterable[str]:
    for dp, _, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith(".dcm") or "." not in fn:
                yield os.path.join(dp, fn)

def index_series(root: str) -> Dict[str, Dict]:
    import pydicom
    series: Dict[str, Dict] = {}
    for fp in walk_dicoms(root):
        try:
            ds = pydicom.dcmread(fp, stop_before_pixels=True, force=True)
        except Exception:
            continue
        sid = getattr(ds, "SeriesInstanceUID", None)
        if not sid: continue
        rec = series.setdefault(sid, {
            "files": [],
            "ProtocolName": getattr(ds, "ProtocolName", "") or "",
            "SeriesDescription": getattr(ds, "SeriesDescription", "") or "",
            "Modality": getattr(ds, "Modality", "") or "",
            "SequenceName": getattr(ds, "SequenceName", "") or "",
            "PulseSequenceName": getattr(ds, "PulseSequenceName", "") or "",
            "ImageType": list(getattr(ds, "ImageType", [])) if hasattr(ds, "ImageType") else [],
            "Rows": int(getattr(ds, "Rows", 0) or 0),
            "Columns": int(getattr(ds, "Columns", 0) or 0),
            "Instances": 0,
            "TI": safe_float(getattr(ds, "InversionTime", None)),
            "TR": safe_float(getattr(ds, "RepetitionTime", None)),
            "TE": safe_float(getattr(ds, "EchoTime", None)),
        })
        rec["files"].append(fp)
        rec["Instances"] += 1

    for sid, rec in series.items():
        rec["label"] = " ".join([rec["ProtocolName"], rec["SeriesDescription"]]).strip().lower()
        rec["imgtype"] = ",".join(rec["ImageType"]).upper()
        rec["vox_est"] = rec["Rows"] * rec["Columns"] * rec["Instances"]
    return series

def is_junk(rec: Dict) -> bool:
    if RX_DROP.search(rec["label"]): return True
    it = rec.get("imgtype","")
    if "DERIVED" in it or "SECONDARY" in it or "LOCALIZER" in it: return True
    return False

def is_T1(rec: Dict) -> bool:
    lab = rec["label"]
    seq = (rec.get("SequenceName","") or "").lower()
    if any(k in lab for k in ["mprage","mp2rage","t1w"]) or re.search(r"\bt1\b", lab): return True
    if "mprage" in seq or "mp2rage" in seq: return True
    TI, TR = rec["TI"], rec["TR"]
    if TI and 600 <= TI <= 1500 and TR and TR < 4000: return True
    return False

def is_FLAIR(rec: Dict) -> bool:
    lab = rec["label"]
    if any(k in lab for k in ["flair","dark-fluid","darkfluid"]): return True
    TI, TR = rec["TI"], rec["TR"]
    if TI and TI >= 1800 and TR and TR >= 4000: return True
    return False

def choose_best(series: Dict[str, Dict], kind: str) -> Optional[str]:
    cands: List[Tuple[str,int,int]] = []
    for sid, rec in series.items():
        if (rec.get("Modality","") or "").upper() != "MR": continue
        if is_junk(rec): continue
        if kind=="T1" and is_T1(rec): cands.append((sid, rec["vox_est"], len(rec["files"])))
        if kind=="FLAIR" and is_FLAIR(rec): cands.append((sid, rec["vox_est"], len(rec["files"])))
    if not cands: return None
    cands.sort(key=lambda t: (t[1], t[2]))
    return cands[-1][0]

# ---------- dcm2niix ----------
def copy_series(tmp_root: str, files: List[str]) -> str:
    out = os.path.join(tmp_root, "sel"); os.makedirs(out, exist_ok=True)
    for src in files:
        dst = os.path.join(out, os.path.basename(src))
        if not os.path.exists(dst):
            try: shutil.copy2(src, dst)
            except Exception: pass
    return out

def run_dcm2niix(in_dir: str, out_dir: str, out_name: str, gzip: bool=True, write_json: bool=True, timeout_s: int=0):
    z = "y" if gzip else "n"
    b = "y" if write_json else "n"
    cmd = ["dcm2niix", "-b", b, "-i", "y", "-z", z, "-f", out_name, "-o", out_dir, in_dir]
    rc = stream_run(cmd, timeout_s=timeout_s)
    if rc != 0: raise RuntimeError(f"dcm2niix exit code {rc}")

# ---------- Output helpers ----------
def bids_out(root: str, sub: str, ses: Optional[str]) -> str:
    base = os.path.join(root, f"sub-{sub}")
    if ses: base = os.path.join(base, f"ses-{ses}")
    ensure_dir(base)
    return base

# ---------- CLI ----------
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="FAST: convert only best T1 (and optional FLAIR)")
    ap.add_argument("-i","--input", default=DEFAULT_INPUT, help="DICOM input folder (recursive)")
    ap.add_argument("-o","--bids-root", default=DEFAULT_BIDS_ROOT, help="Output folder")
    ap.add_argument("-s","--subject", default=DEFAULT_SUBJECT, help="Subject label")
    ap.add_argument("--session", default=DEFAULT_SESSION, help="Session label (optional)")
    ap.add_argument("--with-flair", action="store_true", help="Also convert best FLAIR")
    ap.add_argument("--timeout", type=int, default=0, help="Timeout seconds for dcm2niix (0 = none)")
    ap.add_argument("--no-gzip", action="store_true", help="Write .nii instead of .nii.gz")
    ap.add_argument("--no-json", action="store_true", help="Skip JSON sidecars")
    ap.add_argument("--list", action="store_true", help="List candidate series and exit")
    return ap.parse_args()

def main() -> int:
    args = parse_args()
    need_tools()

    dicom_dir = os.path.abspath(args.input)
    if not os.path.isdir(dicom_dir):
        sys.exit(f"❌ Input DICOM directory not found: {dicom_dir}")

    print("→ Scanning headers (fast)…")
    series = index_series(dicom_dir)

    if args.list:
        rows = []
        for sid, rec in series.items():
            kind = "T1" if is_T1(rec) else ("FLAIR" if is_FLAIR(rec) else "-")
            rows.append((kind, rec["vox_est"], sid, rec["label"]))
        rows.sort(key=lambda r: (r[0]!="T1", r[0]!="FLAIR", -r[1]))
        for r in rows:
            print(f"{r[0]:6} vox={r[1]:10}  {r[2]}  | {r[3]}")
        return 0

    t1_sid = choose_best(series, "T1")
    fl_sid = choose_best(series, "FLAIR") if args.with_flair else None

    if not t1_sid and not fl_sid:
        sys.exit("❌ No T1 or FLAIR candidates found. Run with --list to inspect labels.")

    out_dir = bids_out(os.path.abspath(args.bids_root), args.subject, args.session)

    with tempfile.TemporaryDirectory(prefix="d2b_fast_") as tmp:
        if t1_sid:
            print("✓ Selected T1:", series[t1_sid]["label"])
            sel = copy_series(tmp, series[t1_sid]["files"])
            out_name = f"sub-{args.subject}" + (f"_ses-{args.session}" if args.session else "") + "_T1w"
            run_dcm2niix(sel, out_dir, out_name, gzip=(not args.no_gzip), write_json=(not args.no_json), timeout_s=args.timeout)
        if fl_sid and fl_sid != t1_sid:
            print("✓ Selected FLAIR:", series[fl_sid]["label"])
            sel = copy_series(tmp, series[fl_sid]["files"])
            out_name = f"sub-{args.subject}" + (f"_ses-{args.session}" if args.session else "") + "_FLAIR"
            run_dcm2niix(sel, out_dir, out_name, gzip=(not args.no_gzip), write_json=(not args.no_json), timeout_s=args.timeout)

    print("✅ Done. Output:", out_dir)
    return 0

if __name__ == "__main__":
    sys.exit(main())
