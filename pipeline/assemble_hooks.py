#!/usr/bin/env python3
"""
assemble_hooks.py — hook variants on ONE shared body, no body re-render.

    venv/bin/python pipeline/assemble_hooks.py --body body.mp4 \
        --hooks h1=hook1.mp4,h2=hook2.mp4[,h3=...] --out-dir DIR --name new-ad-f25 \
        [--no-loudnorm] [--ref original.mp4] [--min-free-gb 15]

For each hook: DIR/<name>-<hN>.mp4 = hook frames + body frames, frame-exact.

How the join is made (measured, see the docstring at the bottom):
  video  concat demuxer, stream copy, when hook and body have identical codec
         params + SPS/PPS (extradata). Otherwise the HOOK ONLY is re-encoded
         (NVENC) to the body's params; the body is never touched.
         Each part is first stripped to video-only (stream copy) so the concat
         offset is the exact video duration, not the (longer) AAC duration.
  audio  both tracks decoded, hook audio trimmed/padded to exactly the hook's
         video duration, body audio placed right after it (concat filter),
         one AAC encode. No AAC-stream concat, so no priming/padding gap.
         Final audio is trimmed/padded to the total video duration.
  gate   loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000 in that same encode
         (default on; --no-loudnorm keeps the mix as-is).

Checks per output (any FAIL -> exit 1):
  frames    packets == hook frames + body frames
  a/v dur   |audio - video| <= 1 frame
  join      cross-correlation lag of the output vs the body's own first second
            of audio == 0 samples (body audio not shifted), and 5 ms RMS bins
            in join±100 ms track the ideal (numpy-concatenated) reference
  decode    ffmpeg decodes join±1 s with zero errors
  tail      last second of output vs last second of body: lag 0, corr > 0.5
  loudness  volumedetect mean/max printed

Measured 2026-09-02 on new-ad-f10t.mp4 re-encoded as hook (6.0 s) + body (rest):
  - hook piece decoded audio = 6.016 s for 6.000 s of video (AAC frame-fill);
    body piece = 105.259 s for 105.200 s. A stream-level concat would have
    inserted that as a gap. Trimming to video duration puts the body audio
    at exactly the join: xcorr lag 0 samples vs the original at 0/5/60/100 s.
  - frames 3336 = 180 + 3156; output frame 180 == original frame 180
    (mse 0.8) and != frame 179 (mse 29): no duplicate, no drop.
  - loudnorm is transparent in time: output vs original lag 0 / corr 0.999 at
    60/100/108-110.5 s by full-decode sample index. (A first probe using -ss
    seeks "found" tail damage; it was the ORIGINAL's 46.7 ms audio pts gap at
    108.42 s throwing the seek off. Hence: every check indexes full decodes,
    never -ss, and inputs are scanned for pts gaps.)
  - container audio duration metadata differs between runs (111.200 vs
    111.246) while the decoded sample count is identical -> checks decode.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

import numpy as np

SR = 48000
JOIN_WIN = 0.100      # seconds each side of the join for the RMS-bin check
XCORR_WIN = 1.0       # seconds of body audio used for the lag check
BIN = 0.005           # RMS bin size
RMS_TOL_DB = 3.0      # max per-bin deviation from the ideal reference
RMS_FLOOR_DB = -55.0  # bins quieter than this in the reference are ignored
NVENC = ["-c:v", "h264_nvenc", "-preset", "p4", "-tune", "hq", "-rc", "vbr", "-cq", "19", "-b:v", "0"]

VID_KEYS = ["codec_name", "profile", "level", "pix_fmt", "width", "height",
            "r_frame_rate", "avg_frame_rate", "time_base", "color_range", "field_order"]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path, stream, entries, count_packets=False):
    cmd = ["ffprobe", "-v", "error", "-select_streams", stream]
    if count_packets:
        cmd.append("-count_packets")
    cmd += ["-show_entries", "stream=" + ",".join(entries), "-of", "json", path]
    r = run(cmd)
    if r.returncode:
        sys.exit(f"ffprobe failed on {path}: {r.stderr.strip()}")
    st = json.loads(r.stdout).get("streams") or []
    return st[0] if st else {}


def vinfo(path):
    d = probe(path, "v:0", VID_KEYS + ["nb_frames", "duration", "extradata"], count_packets=True)
    # extradata only shows with -show_data; grab it separately
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_data",
             "-show_entries", "stream=extradata", "-of", "json", path])
    try:
        d["extradata"] = json.loads(r.stdout)["streams"][0].get("extradata", "")
    except Exception:
        d["extradata"] = ""
    d["frames"] = int(d.get("nb_read_packets") or d.get("nb_frames") or 0)
    num, den = map(int, d["r_frame_rate"].split("/"))
    d["fps"] = num / den
    d["vdur"] = d["frames"] / d["fps"]
    return d


def ainfo(path):
    d = probe(path, "a:0", ["codec_name", "sample_rate", "channels", "duration", "start_time"])
    d["adur"] = float(d.get("duration") or 0)
    return d


def pcm(path, ss=None, t=None):
    """Decode audio to mono float32 @ SR. ss/t in seconds."""
    cmd = ["ffmpeg", "-v", "error", "-nostdin"]
    if ss is not None:
        cmd += ["-ss", f"{ss:.6f}"]
    if t is not None:
        cmd += ["-t", f"{t:.6f}"]
    cmd += ["-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        sys.exit(f"decode failed on {path}: {r.stderr.decode().strip()}")
    return np.frombuffer(r.stdout, dtype=np.float32)


def db(x):
    r = float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0
    return 20 * np.log10(r) if r > 1e-9 else -180.0


def rms_bins(x, n):
    bins = []
    for i in range(0, len(x) - n + 1, n):
        bins.append(db(x[i:i + n]))
    return np.array(bins)


def xcorr_lag(a, b, max_lag):
    """Lag (samples) at which b best matches a; positive = b is late."""
    a = a - a.mean(); b = b - b.mean()
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    best, best_lag = -1.0, 0
    den = np.sqrt(np.dot(a, a) * np.dot(b, b)) + 1e-12
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            c = np.dot(a[lag:], b[:n - lag])
        else:
            c = np.dot(a[:n + lag], b[-lag:])
        c /= den
        if c > best:
            best, best_lag = c, lag
    return best_lag, best


def pts_gap_scan(path, label):
    """Warn on audio packet pts steps that deviate from the nominal AAC frame (1024/SR)."""
    r = run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "packet=pts_time",
             "-of", "csv=p=0", path])
    pts = [float(x.strip(",")) for x in r.stdout.split() if x.strip(",") and x.strip(",") != "N/A"]
    nominal = 1024 / SR
    bad = [(pts[i], pts[i] - pts[i - 1] - nominal) for i in range(2, len(pts))
           if abs(pts[i] - pts[i - 1] - nominal) > 0.001]
    for t, dev in bad[:5]:
        print(f"  WARN {label}: audio pts gap of {dev * 1000:+.1f} ms at {t:.3f}s — the join+re-encode drops it "
              f"(samples run straight through); audio after that point sits {dev * 1000:+.1f} ms vs a player honouring the gap")
    if len(bad) > 5:
        print(f"  WARN {label}: ... {len(bad)} pts irregularities total")


def volumedetect(path):
    r = run(["ffmpeg", "-v", "info", "-nostdin", "-i", path, "-vn", "-af", "volumedetect", "-f", "null", "-"])
    mean = mx = None
    for line in r.stderr.splitlines():
        if "mean_volume:" in line:
            mean = float(line.split("mean_volume:")[1].split("dB")[0])
        elif "max_volume:" in line:
            mx = float(line.split("max_volume:")[1].split("dB")[0])
    return mean, mx


def video_only(src, dst):
    r = run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", src, "-an", "-sn", "-dn", "-map", "0:v:0",
             "-c:v", "copy", "-movflags", "+faststart", dst])
    if r.returncode:
        sys.exit(f"video-only strip failed: {r.stderr.strip()}")


def reencode_hook_like_body(hook, body_v, dst):
    """Re-encode ONLY the hook (NVENC) to the body's size/fps/pix_fmt/profile/level."""
    lvl = str(body_v.get("level", ""))
    level = f"{int(lvl) // 10}.{int(lvl) % 10}" if lvl.isdigit() else "auto"
    prof = str(body_v.get("profile", "high")).lower().replace(" ", "")
    cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin", "-hwaccel", "cuda", "-i", hook, "-an", "-map", "0:v:0",
           "-vf", f"scale={body_v['width']}:{body_v['height']},fps={body_v['r_frame_rate']},format={body_v['pix_fmt'].replace('yuvj','yuv')}",
           *NVENC, "-profile:v", prof, "-level:v", level, "-movflags", "+faststart", dst]
    r = run(cmd)
    if r.returncode:
        sys.exit(f"hook re-encode failed: {r.stderr.strip()}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--body", required=True)
    ap.add_argument("--hooks", required=True, help="h1=path,h2=path[,h3=path]")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--no-loudnorm", action="store_true")
    ap.add_argument("--ref", help="optional continuous reference (test only): also xcorr the join against it")
    ap.add_argument("--min-free-gb", type=float, default=15.0)
    ap.add_argument("--keep-tmp", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    free_gb = shutil.disk_usage(a.out_dir).free / 1e9
    if free_gb < a.min_free_gb:
        sys.exit(f"REFUSED: only {free_gb:.1f} GB free on {a.out_dir} (need >= {a.min_free_gb:.0f} GB)")
    print(f"free disk on out-dir: {free_gb:.1f} GB")

    hooks = []
    for item in a.hooks.split(","):
        tag, _, path = item.partition("=")
        if not path or not os.path.exists(path):
            sys.exit(f"bad --hooks entry: {item!r}")
        hooks.append((tag.strip(), path))

    body_v, body_a = vinfo(a.body), ainfo(a.body)
    fps = body_v["fps"]
    frame = 1.0 / fps
    print(f"body: {body_v['frames']} frames @ {fps:g} fps = {body_v['vdur']:.3f}s video, "
          f"{body_a['adur']:.3f}s audio ({body_v['codec_name']} {body_v['profile']} L{body_v['level']} "
          f"{body_v['pix_fmt']} {body_v['width']}x{body_v['height']})")
    if abs(body_a["adur"] - body_v["vdur"]) > frame:
        print(f"  WARN body audio is {body_a['adur'] - body_v['vdur']:+.3f}s vs video; output is trimmed/padded to video length")

    tmp = tempfile.mkdtemp(prefix="assemble_hooks_", dir=a.out_dir)
    body_vo = os.path.join(tmp, "body_v.mp4")
    video_only(a.body, body_vo)
    body_all = pcm(a.body)
    ref_all = pcm(a.ref) if a.ref else None
    pts_gap_scan(a.body, "body")

    any_fail = False
    lines = []
    for tag, hook in hooks:
        hv, ha = vinfo(hook), ainfo(hook)
        hdur = hv["vdur"]
        pts_gap_scan(hook, tag)
        hook_all = pcm(hook)
        mismatch = [k for k in VID_KEYS + ["extradata"] if str(hv.get(k)) != str(body_v.get(k))]
        hook_vo = os.path.join(tmp, f"{tag}_v.mp4")
        if mismatch:
            print(f"[{tag}] hook differs from body on {mismatch} -> re-encoding HOOK only (NVENC); body untouched")
            reencode_hook_like_body(hook, body_v, hook_vo)
            hv2 = vinfo(hook_vo)
            if hv2["frames"] != hv["frames"]:
                print(f"  WARN re-encoded hook has {hv2['frames']} frames (source {hv['frames']})")
            hv = hv2; hdur = hv["vdur"]
        else:
            print(f"[{tag}] hook matches body params + SPS/PPS -> video stream copy")
            video_only(hook, hook_vo)
        print(f"  hook: {hv['frames']} frames = {hdur:.3f}s video, {ha['adur']:.3f}s audio "
              f"(audio-video {ha['adur'] - hdur:+.4f}s)")

        # tail of the hook audio that lies past its last frame: is it audible?
        tail = hook_all[round(hdur * SR):]
        if len(tail) and db(tail) > -50:
            print(f"  WARN hook audio past last frame is audible ({db(tail):.1f} dBFS, {len(tail)/SR*1000:.1f} ms) and gets trimmed")

        total_frames = hv["frames"] + body_v["frames"]
        total_dur = total_frames / fps
        lst = os.path.join(tmp, f"{tag}_list.txt")
        with open(lst, "w") as f:
            f.write(f"file '{hook_vo}'\nfile '{body_vo}'\n")

        # trims/pads by SAMPLE COUNT and pts reset from the sample counter, so an input whose
        # audio pts have a gap (seen in the wild: 46.7 ms at 108.42 s of new-ad-f10t.mp4) cannot
        # shift a time-based trim.
        hs, ts = round(hdur * SR), round(total_dur * SR)
        gate = f"atrim=end_sample={ts},apad=whole_len={ts}"
        if not a.no_loudnorm:
            gate += f",loudnorm=I=-14:TP=-1.5:LRA=11"
        gate += f",aresample={SR},asetpts=N/SR/TB"
        fc = (f"[1:a]aresample={SR},aformat=channel_layouts=stereo,asetpts=N/SR/TB,atrim=end_sample={hs},apad=whole_len={hs}[a0];"
              f"[2:a]aresample={SR},aformat=channel_layouts=stereo,asetpts=N/SR/TB[a1];"
              f"[a0][a1]concat=n=2:v=0:a=1,{gate}[a]")
        out = os.path.join(a.out_dir, f"{a.name}-{tag}.mp4")
        cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin",
               "-f", "concat", "-safe", "0", "-i", lst, "-i", hook, "-i", a.body,
               "-filter_complex", fc, "-map", "0:v:0", "-c:v", "copy", "-map", "[a]",
               "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-movflags", "+faststart", out]
        r = run(cmd)
        if r.returncode:
            sys.exit(f"[{tag}] assemble failed: {r.stderr.strip()}")

        # ---- checks -------------------------------------------------------
        ov, oa = vinfo(out), ainfo(out)
        checks = {}
        checks["frames"] = (ov["frames"] == total_frames, f"{ov['frames']} vs {total_frames} expected")
        out_all = pcm(out)
        adur = len(out_all) / SR
        checks["a/v dur"] = (abs(adur - ov["vdur"]) <= frame, f"decoded audio {adur:.4f}s video {ov['vdur']:.3f}s (d={adur - ov['vdur']:+.4f}s; container says {oa['adur']:.3f}s)")

        # tail: last second of output vs last second of the body (catches EOF filter damage)
        bts, W = round(body_v["vdur"] * SR), round(XCORR_WIN * SR)
        body_tail = body_all[bts - W:bts]
        out_tail = out_all[ts - W:ts]
        tlag, tcorr = xcorr_lag(body_tail, out_tail, max_lag=int(0.010 * SR))
        checks["tail"] = (tlag == 0 and tcorr > 0.5, f"last {XCORR_WIN:g}s vs body: lag {tlag} samples ({tlag / SR * 1000:+.2f} ms), corr {tcorr:.3f}")

        # body audio placement: output[hdur : hdur+1s] vs body[0:1s]
        lag, corr = xcorr_lag(body_all[:W], out_all[hs:hs + W], max_lag=int(0.010 * SR))
        checks["join lag"] = (lag == 0 and corr > 0.5, f"body audio lag {lag} samples ({lag / SR * 1000:+.2f} ms), corr {corr:.3f}")

        # join continuity: 5 ms RMS bins in join±100 ms vs ideal numpy-concat reference
        J = round(JOIN_WIN * SR)
        ref = np.concatenate([hook_all[hs - J:hs], body_all[:J]])
        got = out_all[hs - J:hs + J]
        n = int(BIN * SR)
        rb, gb = rms_bins(ref, n), rms_bins(got, n)
        m = min(len(rb), len(gb))
        rb, gb = rb[:m], gb[:m]
        live = rb > RMS_FLOOR_DB
        if a.no_loudnorm:
            diff = np.abs(gb - rb)
        else:
            # loudnorm shifts the level; compare bin shapes after removing the median offset
            off = np.median(gb[live] - rb[live]) if live.any() else 0.0
            diff = np.abs((gb - off) - rb)
        worst = float(diff[live].max()) if live.any() else 0.0
        checks["join rms"] = (worst <= RMS_TOL_DB, f"worst 5ms-bin deviation {worst:.2f} dB over {int(live.sum())} live bins (ref {db(ref):.1f} dBFS, out {db(got):.1f} dBFS)")

        # optional: against a continuous reference (test only)
        if a.ref:
            ref_win = ref_all[hs - W // 2:hs + W // 2]
            got_win = out_all[hs - W // 2:hs + W // 2]
            lag2, corr2 = xcorr_lag(ref_win, got_win, max_lag=int(0.010 * SR))
            checks["ref lag"] = (lag2 == 0 and corr2 > 0.5, f"vs --ref around join: lag {lag2} samples ({lag2 / SR * 1000:+.2f} ms), corr {corr2:.3f}")

        # decode across the join must be error-free (catches SPS/PPS mismatch after a re-encode)
        d = run(["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{max(hdur - 1, 0):.3f}", "-t", "2", "-i", out, "-f", "null", "-"])
        errs = d.stderr.strip()
        checks["decode"] = (errs == "", "clean" if not errs else errs.splitlines()[0][:120])

        mean, mx = volumedetect(out)
        ok = all(v[0] for v in checks.values())
        any_fail |= not ok
        for k, (p, msg) in checks.items():
            print(f"  {'ok  ' if p else 'FAIL'} {k:9s} {msg}")
        line = (f"{'PASS' if ok else 'FAIL'} {out}  {ov['vdur']:.3f}s  {ov['frames']} frames  "
                f"mean {mean} dB  max {mx} dB")
        lines.append(line)
        print("  " + line)

    if not a.keep_tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    for l in lines:
        print(l)
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
