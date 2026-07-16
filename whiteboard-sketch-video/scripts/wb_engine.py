"""Whiteboard draw-on engine: PNG line art -> stroke-ordered reveal animation.
Order map approach: every ink pixel gets a draw-time index following a pen-like
walk along the stroke skeleton. Black strokes first, colored annotations last.
"""
import cv2
import numpy as np
from scipy import ndimage


def build_order(img_bgr, white_thresh=235, sat_thresh=60, group_dilate=9):
    """Return (order_map float32 0..1 for ink px, -1 elsewhere; pen_path list of (order, x, y))."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    ink = gray < white_thresh
    colored_core = ink & (hsv[..., 1] > sat_thresh)
    # absorb only LIGHT anti-aliased halo pixels around colored strokes/fills;
    # dark black outlines hugging a colored fill must stay in the sketch layer
    k5 = np.ones((7, 7), np.uint8)
    halo = ink & (cv2.dilate(colored_core.astype(np.uint8), k5) > 0) & (gray > 150)
    colored = colored_core | halo
    black = ink & ~colored

    H, W = gray.shape
    order = np.full((H, W), -1.0, dtype=np.float64)
    pen_path = []
    counter = 0

    for layer in (black, colored):
        if not layer.any():
            continue
        k = np.ones((group_dilate, group_dilate), np.uint8)
        merged = cv2.dilate(layer.astype(np.uint8), k)
        n, labels = cv2.connectedComponents(merged)
        comps = []
        for i in range(1, n):
            mask = (labels == i) & layer
            npx = int(mask.sum())
            if npx < 12:  # skip specks (still reveal them at end of layer)
                order[mask] = -2  # mark: assign later
                continue
            ys, xs = np.nonzero(mask)
            comps.append({'mask': mask, 'cx': xs.mean(), 'cy': ys.mean(),
                          'x0': xs.min(), 'y0': ys.min()})
        # component order: greedy nearest neighbor starting top-left
        rem = comps[:]
        cur = None
        seq = []
        if rem:
            rem.sort(key=lambda c: c['y0'] * 0.7 + c['x0'] * 0.3)
            cur = rem.pop(0)
            seq.append(cur)
        while rem:
            d = [((c['cx'] - cur['cx']) ** 2 + (c['cy'] - cur['cy']) ** 2, j)
                 for j, c in enumerate(rem)]
            _, j = min(d)
            cur = rem.pop(j)
            seq.append(cur)
        for c in seq:
            counter = _order_component(c['mask'], order, counter, pen_path)

    # leftover specks: reveal at the very end quickly
    specks = order == -2
    if specks.any():
        order[specks] = counter
        counter += 1

    maxo = max(counter, 1)
    norm = np.where(order >= 0, order / maxo, -1.0).astype(np.float32)
    pen = [(o / maxo, x, y) for (o, x, y) in pen_path]
    return norm, pen


def _order_component(mask, order, counter, pen_path):
    """Walk the skeleton like a pen; map every ink px to nearest skeleton px order."""
    from skimage.morphology import skeletonize
    skel = skeletonize(mask)
    if not skel.any():
        order[mask] = counter
        return counter + 1
    pts = np.column_stack(np.nonzero(skel))  # (y, x)
    ptset = {}
    for idx, (y, x) in enumerate(pts):
        ptset[(y, x)] = idx
    visited = np.zeros(len(pts), bool)
    skorder = np.zeros(len(pts), np.float64)

    def neighbors(y, x):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                j = ptset.get((y + dy, x + dx))
                if j is not None and not visited[j]:
                    yield j

    # endpoints = skeleton px with exactly 1 neighbor
    def nb_count(y, x):
        return sum(1 for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                   if not (dy == 0 and dx == 0) and (y + dy, x + dx) in ptset)

    start = None
    best = 1e18
    for idx, (y, x) in enumerate(pts):
        if nb_count(y, x) == 1:
            score = y * 0.7 + x * 0.3
            if score < best:
                best, start = score, idx
    if start is None:
        start = int(np.argmin(pts[:, 0] * 0.7 + pts[:, 1] * 0.3))

    c = counter
    cur = start
    stamp_every = 6  # record pen pos every N steps
    step = 0
    while True:
        visited[cur] = True
        skorder[cur] = c
        y, x = pts[cur]
        if step % stamp_every == 0:
            pen_path.append((c, int(x), int(y)))
        step += 1
        c += 1
        nxt = None
        nd = 1e18
        for j in neighbors(y, x):
            d = (pts[j][0] - y) ** 2 + (pts[j][1] - x) ** 2
            if d < nd:
                nd, nxt = d, j
        if nxt is None:
            unv = np.nonzero(~visited)[0]
            if len(unv) == 0:
                break
            d2 = (pts[unv, 0] - y) ** 2 + (pts[unv, 1] - x) ** 2
            nxt = unv[int(np.argmin(d2))]
        cur = nxt

    # map every ink pixel to order of nearest skeleton pixel
    _, (iy, ix) = ndimage.distance_transform_edt(~skel, return_indices=True)
    so = np.zeros(mask.shape, np.float64)
    so[pts[:, 0], pts[:, 1]] = skorder
    fill = so[iy, ix]
    order[mask] = fill[mask]
    return c


def render_video(img_path, out_path, draw_seconds=5.0, hold_seconds=1.5,
                 fps=30, canvas=None, pen_png=None, npy_cache=None):
    """Render draw-on animation of img to mp4. canvas=(W,H) places image centered."""
    import subprocess, os
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    if npy_cache and os.path.exists(npy_cache):
        d = np.load(npy_cache, allow_pickle=True).item()
        order, pen = d['order'], d['pen']
    else:
        order, pen = build_order(img)
        if npy_cache:
            np.save(npy_cache, {'order': order, 'pen': pen})
    H, W = order.shape
    total = int((draw_seconds + hold_seconds) * fps)
    draw_f = int(draw_seconds * fps)
    pen_img = None
    if pen_png:
        pen_img = cv2.imread(pen_png, cv2.IMREAD_UNCHANGED)

    cw, ch = canvas if canvas else (W, H)
    ox, oy = (cw - W) // 2, (ch - H) // 2
    white_full = np.full((ch, cw, 3), 255, np.uint8)

    pen_arr = np.array([(o, x, y) for o, x, y in pen]) if pen else None

    cmd = ['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
           '-s', f'{cw}x{ch}', '-r', str(fps), '-i', '-',
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '17',
           '-pix_fmt', 'yuv420p', out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for f in range(total):
        t = min(f / max(draw_f - 1, 1), 1.0)
        frame = white_full.copy()
        reveal = (order >= 0) & (order <= t)
        sub = frame[oy:oy + H, ox:ox + W]
        sub[reveal] = img[reveal]
        if pen_img is not None and t < 1.0 and pen_arr is not None:
            i = int(np.searchsorted(pen_arr[:, 0], t))
            i = min(i, len(pen_arr) - 1)
            _, px, py = pen_arr[i]
            _blit(frame, pen_img, int(px) + ox, int(py) + oy)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    return out_path


def _blit(frame, rgba, x, y):
    """Alpha-blit pen image so its nib (bottom-left corner) sits at (x,y)."""
    ph, pw = rgba.shape[:2]
    x0, y0 = x, y - ph  # nib at bottom-left of pen art
    H, W = frame.shape[:2]
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    w = min(pw - sx0, W - dx0)
    h = min(ph - sy0, H - dy0)
    if w <= 0 or h <= 0:
        return
    src = rgba[sy0:sy0 + h, sx0:sx0 + w]
    a = (src[..., 3:4].astype(np.float32)) / 255.0
    dst = frame[dy0:dy0 + h, dx0:dx0 + w]
    frame[dy0:dy0 + h, dx0:dx0 + w] = (src[..., :3] * a + dst * (1 - a)).astype(np.uint8)


if __name__ == '__main__':
    import sys, time
    t0 = time.time()
    render_video(sys.argv[1], sys.argv[2],
                 draw_seconds=float(sys.argv[3]) if len(sys.argv) > 3 else 5.0,
                 pen_png=sys.argv[4] if len(sys.argv) > 4 else None)
    print('done in', round(time.time() - t0, 1), 's')
