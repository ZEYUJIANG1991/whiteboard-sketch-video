"""Whiteboard video composer: title + illustration draw-on + captions -> silent mp4.

Usage:  .venv/bin/python compose.py <project.json> [preview_scene_index]

project.json lives in the working project dir; brand.json is resolved from the
project's "brand" field: a path, or a pack name under this skill's brand/ dir.
All brand-specific knobs (canvas, fonts, colors, layout, pointer) live in
brand.json; all per-video data (scenes, frame table, captions) in project.json.
"""
import cv2, re, os, sys, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from wb_engine import build_order

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config(project_path):
    proj = json.load(open(project_path))
    b = proj.get("brand", "default")
    for cand in (b, os.path.join(SKILL_DIR, "brand", b, "brand.json"),
                 os.path.join(b, "brand.json")):
        if os.path.isfile(cand):
            brand = json.load(open(cand)); break
    else:
        raise FileNotFoundError(f"brand pack not found: {b}")
    return proj, brand


def resolve_font(font_cfg):
    for p in [font_cfg.get("path", "")] + font_cfg.get("fallbacks", []):
        p = os.path.expanduser(p)
        if p and os.path.isfile(p):
            return p
    raise FileNotFoundError("no usable font; set brand.json fonts.path")


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def autocrop_scale(path, box, contrast=1.15):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"illustration not readable: {path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ys, xs = np.nonzero(gray < 245)
    if len(xs) == 0:
        raise ValueError(f"illustration appears blank (all white): {path}")
    pad = 30
    y0, y1 = max(ys.min()-pad, 0), min(ys.max()+pad, img.shape[0])
    x0, x1 = max(xs.min()-pad, 0), min(xs.max()+pad, img.shape[1])
    img = img[y0:y1, x0:x1]
    h, w = img.shape[:2]
    s = min(box[0]/w, box[1]/h)
    img = cv2.resize(img, (int(w*s), int(h*s)), interpolation=cv2.INTER_AREA)
    return np.clip(img.astype(np.float32)*contrast - 20, 0, 255).astype(np.uint8)


def render_text_img(text, size, font_path, rgb, canvas_w):
    f = ImageFont.truetype(font_path, size)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    while size > 24 and probe.textlength(text, font=f) > canvas_w - 80:
        size -= 4
        f = ImageFont.truetype(font_path, size)
    im = Image.new("RGB", (canvas_w, int(size*1.6)), "white")
    d = ImageDraw.Draw(im)
    tw = d.textlength(text, font=f)
    d.text(((canvas_w-tw)//2, int(size*0.15)), text, font=f, fill=rgb)
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def parse_captions(path, fps):
    """Accept align_captions.py .ts output OR standard .srt. Missing/empty -> no captions."""
    if not path or not os.path.isfile(path):
        return []
    src = open(path, encoding='utf-8').read().strip()
    if not src:
        return []
    caps = []
    if path.endswith('.srt') or ' --> ' in src[:500]:
        for b in re.split(r'\n\s*\n', src):
            m = re.search(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', b)
            if not m:
                continue
            g = list(map(int, m.groups()))
            t0 = g[0]*3600 + g[1]*60 + g[2] + g[3]/1000
            t1 = g[4]*3600 + g[5]*60 + g[6] + g[7]/1000
            text = ' '.join(l.strip() for l in b[m.end():].splitlines() if l.strip())
            if text:
                caps.append((text, int(round(t0*fps)), int(round(t1*fps))))
    else:
        for m in re.finditer(r"\{ t0: ([\d.]+), t1: ([\d.]+), text: '([^']+)' \}", src):
            caps.append((m.group(3), int(round(float(m.group(1))*fps)),
                         int(round(float(m.group(2))*fps))))
    return caps


def make_pen():
    """Minimal line-art marker, nib at bottom-left. Used when pointer.mode=pen."""
    S = 120
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    nib = (10, S - 10)
    d.polygon([nib, (28, S - 48), (48, S - 28)], outline=(30, 30, 30, 255),
              fill=(70, 70, 70, 255))
    d.polygon([(28, S - 48), (48, S - 28), (100, S - 80), (80, S - 100)],
              outline=(30, 30, 30, 255), fill=(255, 255, 255, 255))
    d.line([(88, S - 68), (68, S - 88)], fill=(30, 30, 30, 255), width=4)
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGBA2BGRA), 'bottom-left'


def load_hand(path, target_h):
    """Photo hand holding a marker; nib assumed at top-left of alpha bbox."""
    rgba = cv2.imread(os.path.expanduser(path), cv2.IMREAD_UNCHANGED)
    a = rgba[..., 3]
    ys, xs = np.nonzero(a > 10)
    rgba = rgba[ys.min():ys.max()+1, xs.min():xs.max()+1]
    s = target_h / rgba.shape[0]
    rgba = cv2.resize(rgba, (max(1, int(rgba.shape[1]*s)), target_h),
                      interpolation=cv2.INTER_AREA)
    return rgba, 'top-left'


def blit_rgba(frame, rgba, x, y, anchor):
    ph, pw = rgba.shape[:2]
    x0, y0 = (x, y - ph) if anchor == 'bottom-left' else (x - 6, y - 6)
    H, W = frame.shape[:2]
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    w = min(pw - sx0, W - dx0); h = min(ph - sy0, H - dy0)
    if w <= 0 or h <= 0: return
    src = rgba[sy0:sy0+h, sx0:sx0+w]
    a = src[..., 3:4].astype(np.float32) / 255.0
    dst = frame[dy0:dy0+h, dx0:dx0+w]
    frame[dy0:dy0+h, dx0:dx0+w] = (src[..., :3]*a + dst*(1-a)).astype(np.uint8)


def main(project_path, preview_scene=None):
    proj, brand = load_config(project_path)
    os.chdir(os.path.dirname(os.path.abspath(project_path)) or '.')
    fps = proj.get("fps", 30)
    W, H = brand["canvas"]["w"], brand["canvas"]["h"]
    ink = hex_rgb(brand.get("ink_hex", "#141414"))
    tfont = resolve_font(brand["fonts"]["title"])
    cfont = resolve_font(brand["fonts"]["caption"])
    T, C, IL = brand["title"], brand["caption"], brand["illustration"]
    total = proj["total_frames"] + proj.get("tail_frames", 60)

    caps = parse_captions(proj.get("captions"), fps)
    cap_imgs = {(s, e): render_text_img(t, C["size"], cfont, ink, W)
                for t, s, e in caps}

    scene_cfgs = proj["scenes"]
    scenes = []
    for i, sc in enumerate(scene_cfgs):
        end = scene_cfgs[i+1]["start"] if i+1 < len(scene_cfgs) else total
        if preview_scene is not None and i != preview_scene:
            scenes.append(dict(start=sc["start"], end=end)); continue
        img = autocrop_scale(sc["image"], (IL["max_w"], IL["max_h"]))
        order, pen = build_order(img)
        tim = render_text_img(sc.get("title", ""), T["size"], tfont, ink, W) \
            if sc.get("title") else None
        torder, tpen = build_order(tim) if tim is not None else (None, None)
        scenes.append(dict(start=sc["start"], end=end, img=img, order=order,
                           pen=pen, tim=tim, torder=torder, tpen=tpen))
        print(f"scene {i+1} prepared: {sc['image']} {img.shape}", flush=True)

    pm = brand.get("pointer", {"mode": "pen"})
    if pm["mode"] == "hand":
        pen_img, anchor = load_hand(pm["hand_asset"], pm.get("hand_height", 430))
    elif pm["mode"] == "pen":
        pen_img, anchor = make_pen()
    else:
        pen_img, anchor = None, None

    white = np.full((H, W, 3), 255, np.uint8)
    rng = range(total) if preview_scene is None else \
        range(scenes[preview_scene]['start'], scenes[preview_scene]['end'])
    out_path = proj.get("out", "silent.mp4")
    if preview_scene is not None:  # never clobber the full render with a preview
        root, ext = os.path.splitext(out_path)
        out_path = f"{root}.preview{preview_scene}{ext}"
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-c:v', 'libx264',
           '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    tdraw_f = int(T.get("draw_seconds", 0.7) * fps)

    for f in rng:
        sc = next((s for s in scenes if s['start'] <= f < s['end']), scenes[-1])
        lf = f - sc['start']
        frame = white.copy()
        pen_xy = None
        if sc.get('tim') is not None:
            tt = min(lf / max(tdraw_f-1, 1), 1.0)
            th, tw = sc['torder'].shape
            sub = frame[T["y"]:T["y"]+th, 0:tw]
            rev = (sc['torder'] >= 0) & (sc['torder'] <= tt)
            sub[rev] = sc['tim'][rev]
            if tt < 1.0 and sc['tpen']:
                arr = sc['tpen']
                _, px, py = arr[min(int(tt*len(arr)), len(arr)-1)]
                pen_xy = (int(px), int(py)+T["y"])
        if sc.get('img') is not None:
            dur = sc['end'] - sc['start']
            draw_f = int(dur * IL.get("draw_frac", 0.6))
            it = max(0.0, min((lf - tdraw_f) / max(draw_f-1, 1), 1.0))
            ih, iw = sc['order'].shape
            ox, oy = (W-iw)//2, IL["cy"] - ih//2
            if it > 0:
                sub = frame[oy:oy+ih, ox:ox+iw]
                rev = (sc['order'] >= 0) & (sc['order'] <= it)
                sub[rev] = sc['img'][rev]
                if it < 1.0 and sc['pen']:
                    arr = sc['pen']
                    _, px, py = arr[min(int(it*len(arr)), len(arr)-1)]
                    pen_xy = (int(px)+ox, int(py)+oy)
        if pen_img is not None and pen_xy is not None:
            blit_rgba(frame, pen_img, pen_xy[0], pen_xy[1], anchor)
        for (s_, e_), cim in cap_imgs.items():
            if s_ <= f < e_:
                chh, cww = cim.shape[:2]
                mask = cv2.cvtColor(cim, cv2.COLOR_BGR2GRAY) < 250
                sub = frame[C["y"]:C["y"]+chh, 0:cww]
                sub[mask] = cim[mask]
                break
        proc.stdin.write(frame.tobytes())
        if f % 300 == 0:
            print(f"frame {f}/{total}", flush=True)
    proc.stdin.close(); proc.wait()
    print("silent video done:", out_path)


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
