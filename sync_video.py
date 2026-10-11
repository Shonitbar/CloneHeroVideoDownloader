#!/usr/bin/env python3
"""
Estimate video_start_time for YARG/Clone Hero song.ini by cross-correlating
the audio track of a downloaded music video against the chart's audio.

Usage:
    python sync_video.py <root_folder> [--apply] [--overwrite] [--min-prominence 6.0]

Can also be imported: sync_folder() processes a single song folder and is
what the Clone Hero Video Downloader GUI calls after each download.

For each song folder containing song.ogg, video.webm and song.ini, this
decodes the chart audio (all .ogg stems summed) and the video's audio track
to low-res mono PCM with ffmpeg, does a coarse FFT cross-correlation on the
amplitude envelope to find the rough lag, then refines that lag with a
direct sample-domain correlation for millisecond precision.

Positive result  -> video has MORE lead-in than the audio -> video_start_time
                    should be positive (skip forward into the video).
Negative result  -> video has LESS lead-in than the audio -> video_start_time
                    should be negative (delay video playback).

By default the CLI only prints a report. Pass --apply to write
video_start_time into each song.ini (a .bak backup of the original is kept).
Songs that already have video_start_time are skipped unless --overwrite.
"""
import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

COARSE_SR = 1000       # Hz, for the envelope-based coarse search
FINE_SR = 8000         # Hz, for the ms-precision refinement
COARSE_WINDOW_S = 400  # only look at the first N seconds of each track
FINE_HALFWIDTH_S = 2.0 # +/- window around the coarse estimate to refine in
DEFAULT_MIN_PROMINENCE = 6.0


def resolve_ffmpeg(preferred: str | None = None) -> str:
    if preferred:
        return preferred
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which("ffmpeg") or "ffmpeg"


def decode_audio(path: Path, sr: int, ffmpeg: str, duration: float | None = None) -> np.ndarray:
    """Decode an audio/video file's audio track to mono float32 PCM via ffmpeg."""
    cmd = [ffmpeg, "-v", "error", "-i", str(path)]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += ["-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    # Avoid a console window flashing up for every decode when called from a GUI
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {path}: {proc.stderr.decode(errors='replace')[:500]}")
    return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def decode_song_mix(folder: Path, sr: int, ffmpeg: str, duration: float | None = None) -> np.ndarray:
    """Reconstruct the full mix by summing every .ogg stem in the folder.

    Some charts split the track into stems (guitar.ogg, vocals.ogg, drums.ogg,
    ...) with song.ogg left as just a quiet/silent backing track. Official
    music videos contain the full mix, so comparing against song.ogg alone
    can badly misalign (or just fail to correlate). Summing all stems
    reconstructs the same full mix the game plays during gameplay.
    """
    ogg_files = sorted(folder.glob("*.ogg"))
    if not ogg_files:
        raise RuntimeError(f"No .ogg files found in {folder}")
    stems = [decode_audio(f, sr, ffmpeg, duration=duration) for f in ogg_files]
    max_len = max(len(s) for s in stems)
    mix = np.zeros(max_len, dtype=np.float32)
    for s in stems:
        mix[: len(s)] += s
    return mix


def envelope(sig: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    """Rectify + decimate to a coarse amplitude envelope robust to mix/EQ differences."""
    rect = np.abs(sig)
    factor = max(1, src_sr // dst_sr)
    n = (len(rect) // factor) * factor
    env = rect[:n].reshape(-1, factor).mean(axis=1)
    return env - env.mean()


def best_lag_fft(a: np.ndarray, b: np.ndarray):
    """Find the lag L (in samples) such that b[L : L+len(a)] best matches a.

    Returns (lag_samples, cosine_similarity, prominence).

    cosine_similarity (~0..1) is how acoustically alike the two tracks are at
    the best lag. It's low whenever the video uses a different mix/performance
    than the chart audio EVEN IF the alignment is correct, so it's a poor
    measure of "did we find the right offset".

    prominence is a z-score: how far the best peak stands out above the
    correlation at every other candidate lag. A genuine timing match produces
    a distinct peak regardless of how similar the mixes sound; a spurious
    match looks like the noise floor. This is the confidence signal to use.
    """
    corr = fftconvolve(b, a[::-1], mode="full")
    # corr index i corresponds to lag = i - (len(a) - 1)
    lags = np.arange(len(corr)) - (len(a) - 1)
    best_idx = int(np.argmax(corr))
    lag = int(lags[best_idx])

    baseline = np.delete(corr, best_idx)
    prominence = float((corr[best_idx] - baseline.mean()) / (baseline.std() + 1e-9))

    start_b = max(0, lag)
    start_a = max(0, -lag)
    length = min(len(a) - start_a, len(b) - start_b)
    if length <= 1:
        return lag, 0.0, prominence
    aw = a[start_a:start_a + length]
    bw = b[start_b:start_b + length]
    denom = np.sqrt(np.sum(aw * aw) * np.sum(bw * bw))
    cosine_similarity = float(corr[best_idx] / denom) if denom > 0 else 0.0
    return lag, cosine_similarity, prominence


def estimate_offset_ms(folder: Path, video_webm: Path, ffmpeg: str):
    # Stage 1: coarse search using a 1kHz envelope
    a_full = decode_song_mix(folder, FINE_SR, ffmpeg, duration=COARSE_WINDOW_S)
    b_full = decode_audio(video_webm, FINE_SR, ffmpeg, duration=COARSE_WINDOW_S)

    coarse_lag_samples, _, _ = best_lag_fft(envelope(a_full, FINE_SR, COARSE_SR),
                                            envelope(b_full, FINE_SR, COARSE_SR))
    coarse_lag_s = coarse_lag_samples / COARSE_SR

    # Stage 2: refine against the first 20s of chart audio in a small window
    # around the coarse estimate, at full resolution
    ref_len_s = min(20.0, len(a_full) / FINE_SR)
    a_ref = a_full[: int(ref_len_s * FINE_SR)]

    lo_sample = int(max(0.0, coarse_lag_s - FINE_HALFWIDTH_S) * FINE_SR)
    hi_sample = int((coarse_lag_s + ref_len_s + FINE_HALFWIDTH_S) * FINE_SR)
    b_window = b_full[lo_sample:hi_sample]

    fine_lag_samples, cosine_similarity, prominence = best_lag_fft(a_ref, b_window)
    offset_ms = round((lo_sample + fine_lag_samples) / FINE_SR * 1000)
    return offset_ms, cosine_similarity, prominence


def has_video_start_time(ini_path: Path) -> bool:
    text = ini_path.read_text(encoding="utf-8-sig")
    return any(line.strip().lower().startswith("video_start_time") for line in text.splitlines())


def update_ini(ini_path: Path, offset_ms: int):
    text = ini_path.read_text(encoding="utf-8-sig")
    out = []
    found = False
    for line in text.splitlines():
        if line.strip().lower().startswith("video_start_time"):
            out.append(f"video_start_time = {offset_ms}")
            found = True
        else:
            out.append(line)
    if not found:
        # insert after [song] header if present, else at top
        final = []
        inserted = False
        for line in out:
            final.append(line)
            if not inserted and line.strip().lower() == "[song]":
                final.append(f"video_start_time = {offset_ms}")
                inserted = True
        if not inserted:
            final.insert(0, f"video_start_time = {offset_ms}")
        out = final

    backup = ini_path.with_suffix(ini_path.suffix + ".bak")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")
    ini_path.write_text("\n".join(out) + "\n", encoding="utf-8")


@dataclass
class SyncResult:
    status: str  # "ok", "low-confidence", "skipped-existing", "missing-files", "error"
    offset_ms: int | None = None
    similarity: float | None = None
    prominence: float | None = None
    applied: bool = False
    message: str = ""


def sync_folder(folder: Path, apply: bool = False, overwrite: bool = False,
                min_prominence: float = DEFAULT_MIN_PROMINENCE,
                ffmpeg: str | None = None) -> SyncResult:
    """Estimate (and optionally write) video_start_time for one song folder."""
    folder = Path(folder)
    video = folder / "video.webm"
    ini = folder / "song.ini"
    if not (video.exists() and ini.exists() and any(folder.glob("*.ogg"))):
        return SyncResult("missing-files", message="needs video.webm, song.ini and .ogg audio")
    if not overwrite and has_video_start_time(ini):
        return SyncResult("skipped-existing", message="song.ini already has video_start_time")
    try:
        offset_ms, similarity, prominence = estimate_offset_ms(folder, video, resolve_ffmpeg(ffmpeg))
    except Exception as e:
        return SyncResult("error", message=str(e))

    status = "ok" if prominence >= min_prominence else "low-confidence"
    result = SyncResult(status, offset_ms, similarity, prominence)
    if apply and status == "ok":
        update_ini(ini, offset_ms)
        result.applied = True
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--apply", action="store_true", help="write video_start_time into song.ini")
    ap.add_argument("--overwrite", action="store_true",
                    help="also (re-)process songs whose song.ini already has a "
                         "video_start_time value; default is to skip them entirely")
    ap.add_argument("--min-prominence", type=float, default=DEFAULT_MIN_PROMINENCE,
                    help="peak-prominence z-score below this is flagged as low-confidence "
                         "instead of applying (this is the primary confidence signal)")
    ap.add_argument("--filter", default=None, help="only process folders containing this substring")
    ap.add_argument("--ffmpeg", default=None, help="path to ffmpeg (default: imageio_ffmpeg, then PATH)")
    args = ap.parse_args()

    results = []
    for folder in sorted(p for p in args.root.iterdir() if p.is_dir()):
        if args.filter and args.filter.lower() not in folder.name.lower():
            continue
        r = sync_folder(folder, args.apply, args.overwrite, args.min_prominence, args.ffmpeg)
        if r.status == "missing-files":
            continue
        results.append((folder.name, r))
        if r.status == "skipped-existing":
            print(f"{folder.name:45s} already has video_start_time, skipping (use --overwrite to redo)")
        elif r.status == "error":
            print(f"{folder.name:45s} ERROR: {r.message}")
        else:
            print(f"{folder.name:45s} offset={r.offset_ms:+6d} ms  similarity={r.similarity:5.3f}  "
                  f"prominence={r.prominence:6.1f}  {r.status.upper()}")

    skipped = sum(1 for _, r in results if r.status == "skipped-existing")
    low = [(n, r) for n, r in results if r.status == "low-confidence"]
    errs = [(n, r) for n, r in results if r.status == "error"]
    print(f"\n{len(results) - skipped} songs processed, {skipped} already had video_start_time (skipped), "
          f"{len(low)} low-confidence, {len(errs)} errors.")
    if low:
        print("Low-confidence (review manually):")
        for n, r in low:
            print(f"  - {n}  (offset={r.offset_ms:+d} ms, similarity={r.similarity:.3f}, "
                  f"prominence={r.prominence:.1f})")
    if errs:
        print("Errors:")
        for n, r in errs:
            print(f"  - {n}: {r.message}")


if __name__ == "__main__":
    sys.exit(main())
