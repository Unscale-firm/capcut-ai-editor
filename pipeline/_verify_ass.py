"""
Verification harness (throwaway): render the SAME 300 frames that Remotion rendered
(bench.mp4, frames 0-299 of the `new-ad` composition) but entirely in ffmpeg, so the
two can be compared frame-by-frame.

Frames 0-299 contain no angle switches and no flash (first CUT is 377), so this isolates
exactly: 1.1x speed + the steady zoom ramp + the burned-in captions.
"""
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
from ass_captions import write_ass

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
VID = r"C:\Users\User\my-video"
SCRATCH = r"C:\Users\User\AppData\Local\Temp\claude\C--Users-User\4a54c0be-7a6a-4690-97b3-0938774f9070\scratchpad"

# from adConfig.ts / AdAuto.tsx
SPEED, FPS = 1.1, 30
ZOOM_A, ZOOM_B = 1.18, 1.42
AD_DUR = 4378
NFRAMES = 300
SS = 3.0   # supersample factor before cropping -> sub-pixel zoom (kills the 1px "stepping")


def load_caps():
    """Pull the CAPTIONS array straight out of the generated captionsData.ts."""
    src = open(os.path.join(VID, "src", "captionsData.ts"), encoding="utf-8").read()
    m = re.search(r"export const CAPTIONS: Cap\[\] = (\[.*\]);", src, re.S)
    return json.loads(m.group(1))


def main():
    caps = load_caps()
    # only the lines that fall inside the benchmark window
    caps = [c for c in caps if c["from"] < NFRAMES]
    ass = os.path.join(SCRATCH, "captions.ass")
    write_ass(caps, ass, FPS)
    print(f"wrote {ass}  ({len(caps)} lines in first {NFRAMES} frames)")

    # Zoom ramp. AdAuto: steady = interpolate(f, [0, AD_DUR], [ZOOM_A, ZOOM_B]).
    # `crop` can't do a moving zoom (its output size is fixed at configure time), so use zoompan.
    # zoompan truncates its x/y to whole INPUT pixels, which makes a slow push visibly "step";
    # running it on a supersampled frame (and keeping s == the supersampled size, so z=1 really
    # means "no zoom") pushes that quantisation down to 1/SS px at the final 1080x1920.
    z = f"({ZOOM_A}+{ZOOM_B - ZOOM_A}*min(1,on/{AD_DUR}))"

    W, H = 1080, 1920
    SW, SH = int(W * SS), int(H * SS)
    vf = (
        f"setpts=PTS/{SPEED},fps={FPS},"
        f"scale={SW}:{SH}:flags=bicubic,"
        # zoompan crops an (ow/zoom, oh/zoom) window out of the INPUT at (x,y) and scales it up to
        # ow x oh, so the centring offset is in input coordinates: x = iw/2 - (ow/zoom)/2.
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={SW}x{SH}:fps={FPS},"
        f"scale={W}:{H}:flags=bicubic,"
        f"ass=filename=captions.ass:fontsdir=fonts"
    )

    out = os.path.join(SCRATCH, "ff_look.mp4")
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error",
           "-i", os.path.join(VID, "public", "ad.mp4"),
           "-vf", vf, "-frames:v", str(NFRAMES),
           "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out]
    print("running ffmpeg...")
    r = subprocess.run(cmd, cwd=SCRATCH, capture_output=True, text=True)
    if r.returncode:
        print("FFMPEG FAILED:\n", r.stderr[-3000:])
        sys.exit(1)
    print("wrote", out)


if __name__ == "__main__":
    main()
