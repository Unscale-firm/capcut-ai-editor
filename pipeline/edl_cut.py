"""
VSL cutter: takes an EXPLICIT edit decision list (ranges in mic time, in order) instead of the
ad heuristic. Pads each range, clamps the pad so it never bleeds into dropped speech, merges
ranges that touch, and writes keep_ranges.json + words_cut.json. --assemble bakes base_cut.mp4.

Run:
  venv/Scripts/python.exe pipeline/edl_cut.py --work work_vsl --edl work_vsl/edl.json \
      --front <front.mp4> --assemble
"""
import json, argparse, os, subprocess

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
PAD = 0.12
GUARD = 0.03   # never come this close to a word we are dropping


def clamp(ranges, words):
    """Expand each range by PAD, but never into a word that is not inside that range.
    A word belongs to a range if its MIDPOINT falls in it — Whisper's boundaries are
    approximate, so strict containment silently drops words that straddle an edge."""
    out = []
    for a, b in ranges:
        mine = [w for w in words if a - 0.05 <= (w["start"] + w["end"]) / 2 <= b + 0.05]
        if mine:                       # snap the range onto the words it actually holds
            a = min(a, mine[0]["start"])
            b = max(b, mine[-1]["end"])
        lo, hi = a - PAD, b + PAD
        for w in words:
            if w in mine:
                continue
            if w["end"] <= a and w["end"] > lo:          # dropped word just before
                lo = max(lo, w["end"] + GUARD)
            if w["start"] >= b and w["start"] < hi:      # dropped word just after
                hi = min(hi, w["start"] - GUARD)
        out.append([round(max(0.0, min(lo, a)), 3), round(max(hi, b), 3)])
    return out


def merge(ranges):
    out = []
    for a, b in ranges:
        if out and a - out[-1][1] < 0.02:
            out[-1][1] = b
        else:
            out.append([a, b])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work_vsl")
    ap.add_argument("--edl", required=True)
    ap.add_argument("--front", default=None)
    ap.add_argument("--side", default=None)
    ap.add_argument("--fps", type=float, default=25.0, help="camera frame rate")
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--assemble-side", action="store_true",
                    help="bake the SIDE angle over the same cuts, so both angles share a timeline")
    a = ap.parse_args()

    words = json.load(open(os.path.join(a.work, "words.json"), encoding="utf-8"))
    off = json.load(open(os.path.join(a.work, "offsets.json")))
    edl = json.load(open(a.edl))

    ranges = merge(clamp(edl, words))

    # Snap every cut onto the camera's frame grid. ffmpeg's video trim can only cut on a frame
    # boundary, so an unsnapped piece keeps ceil(n) frames while its audio piece is sample-exact
    # — a few ms of video surplus per piece. Over 100+ splices that compounds into visible lip-sync
    # lag. Snapped, each piece is a whole number of frames and both streams are the same length.
    fo, fps = off["front"], a.fps
    snapped = []
    for x, y in ranges:
        k0, k1 = round((x + fo) * fps), round((y + fo) * fps)
        if k1 <= k0:
            k1 = k0 + 1
        snapped.append([round(k0 / fps - fo, 4), round(k1 / fps - fo, 4)])
    ranges = snapped

    words_cut, t_out = [], 0.0
    for a0, b0 in ranges:
        for w in words:
            if a0 <= (w["start"] + w["end"]) / 2 <= b0:
                ns = t_out + (w["start"] - a0)
                words_cut.append({"start": round(ns, 3),
                                  "end": round(ns + (w["end"] - w["start"]), 3),
                                  "word": w["word"]})
        t_out += (b0 - a0)

    json.dump(ranges, open(os.path.join(a.work, "keep_ranges.json"), "w"))
    json.dump(words_cut, open(os.path.join(a.work, "words_cut.json"), "w"), ensure_ascii=False)
    src = words[-1]["end"]
    print(f"source {src:.0f}s -> cut {t_out:.0f}s  ({t_out/60:.1f} min)  in {len(ranges)} pieces")
    print(f"removed {src - t_out:.0f}s of silence / retakes / chatter")
    print(f"kept {len(words_cut)} of {len(words)} words")

    if a.assemble:
        assert a.front
        mic_hq = os.path.join(a.work, "mic_hq.wav")
        mic = mic_hq if os.path.exists(mic_hq) else os.path.join(a.work, "audio_mic.wav")
        half = 0.5 / fps          # cut BETWEEN frames, so the frame count is unambiguous
        parts = []
        for i, (x, y) in enumerate(ranges):
            parts.append(f"[0:v]trim=start={x+fo-half:.4f}:end={y+fo-half:.4f},"
                         f"setpts=PTS-STARTPTS[v{i}];")
            parts.append(f"[1:a]atrim=start={x:.4f}:end={y:.4f},asetpts=PTS-STARTPTS[a{i}];")
        fc = "".join(parts) + "".join(f"[v{i}][a{i}]" for i in range(len(ranges))) + \
             f"concat=n={len(ranges)}:v=1:a=1[v][a]"
        fcfile = os.path.join(a.work, "fc.txt")
        open(fcfile, "w").write(fc)
        out = os.path.join(a.work, "base_cut.mp4")
        print("assembling base_cut.mp4 ...")
        r = subprocess.run([FF, "-y", "-i", a.front, "-i", mic, "-filter_complex_script", fcfile,
                            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", out],
                           capture_output=True, text=True)
        print("FFMPEG ERROR:\n" + r.stderr[-1500:] if r.returncode else "wrote " + out)

    if a.assemble_side:
        assert a.side
        so = off["side"]
        half = 0.5 / fps
        mic_hq = os.path.join(a.work, "mic_hq.wav")
        mic = mic_hq if os.path.exists(mic_hq) else os.path.join(a.work, "audio_mic.wav")
        parts = []
        for i, (x, y) in enumerate(ranges):
            # force the SAME frame count as the front piece, so the two angles stay on one
            # timeline — rounding each side piece independently would drift them apart.
            nfr = round((y - x) * fps)
            k0 = round((x + so) * fps)
            parts.append(f"[0:v]trim=start={k0/fps-half:.4f}:end={(k0+nfr)/fps-half:.4f},"
                         f"setpts=PTS-STARTPTS[v{i}];")
            parts.append(f"[1:a]atrim=start={x:.4f}:end={y:.4f},asetpts=PTS-STARTPTS[a{i}];")
        fc = "".join(parts) + "".join(f"[v{i}][a{i}]" for i in range(len(ranges))) + \
             f"concat=n={len(ranges)}:v=1:a=1[v][a]"
        fcfile = os.path.join(a.work, "fc_side.txt")
        open(fcfile, "w").write(fc)
        out = os.path.join(a.work, "side_cut.mp4")
        print("assembling side_cut.mp4 ...")
        r = subprocess.run([FF, "-y", "-i", a.side, "-i", mic, "-filter_complex_script", fcfile,
                            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", out],
                           capture_output=True, text=True)
        print("FFMPEG ERROR:\n" + r.stderr[-1500:] if r.returncode else "wrote " + out)


if __name__ == "__main__":
    main()
