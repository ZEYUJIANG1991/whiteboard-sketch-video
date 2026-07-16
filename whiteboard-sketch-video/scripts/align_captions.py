#!/usr/bin/env python3
"""align_captions.py — FORCED ALIGNMENT: map the KNOWN-CORRECT script text onto whisper
WORD timestamps → short, precisely-timed captions + scene-start frames.

WHY (vs build_captions.py): whisper's per-word TIMINGS are accurate even when its TEXT
is badly garbled (homophones / traditional chars, e.g. 未來上位協救 / en-go的窗口) — too
broken to hand-fix. Since the VO script is OURS and known, never fix ASR text; instead
difflib-align the correct script to the recognized chars (matched chars = time anchors,
gaps linearly interpolated) and emit the correct text with word-accurate times.

Also encodes the caption-line rules learned the hard way (gotchas 坑9):
  - <= MAXLEN (18) visible chars per line — one line in the 42px/960px caption box
  - anti-orphan: a split tail of <=2 chars merges back (no lonely 「赛」 line)
  - token-aware: never break inside a Latin word/name; a Latin token that would land
    on a full line's tail starts the next line instead (keeps "Demis Hassabis" whole)

Usage:
  python3 align_captions.py /tmp/vo.json script.txt [--fps 30] [--maxlen 18]
      [--const CAPTIONS2] [--anchors anchors.txt] > src/captions2.ts
  anchors.txt: one substring per line = the first words of scenes 2..N (scene 1 = frame 0);
  matched IN ORDER against the script. stderr prints scene start frames + durations
  (use as Sequence from/durationInFrames) and the total composition frame count.
"""
import json, sys, re, difflib, argparse

p = argparse.ArgumentParser()
p.add_argument("whisper_json")
p.add_argument("script_txt")
p.add_argument("--fps", type=int, default=30)
p.add_argument("--maxlen", type=int, default=18)
p.add_argument("--const", default="CAPTIONS2")
p.add_argument("--anchors", default=None)
args = p.parse_args()

data = json.load(open(args.whisper_json))
R_chars, R_start = [], []
for seg in data.get("segments", []):
    for w in seg.get("words", []):
        txt = (w.get("word") or "").strip()
        if not txt:
            continue
        s, e = float(w["start"]), float(w["end"])
        for i, ch in enumerate(txt):
            R_chars.append(ch)
            R_start.append(s + (e - s) * i / len(txt))
R = "".join(R_chars)
if not R_start:
    sys.exit("no words in whisper json")
audio_end = R_start[-1] + 0.4

S = "".join(ln.strip() for ln in open(args.script_txt).read().splitlines() if ln.strip())

# --- align correct script S onto recognized R; matched chars anchor the timeline ---
sm = difflib.SequenceMatcher(a=S, b=R, autojunk=False)
S_time = [None] * len(S)
for blk in sm.get_matching_blocks():
    for k in range(blk.size):
        S_time[blk.a + k] = R_start[blk.b + k]
known = [i for i, t in enumerate(S_time) if t is not None]
for i in range(known[0]):
    S_time[i] = S_time[known[0]]
for i in range(known[-1] + 1, len(S)):
    S_time[i] = S_time[known[-1]]
for a, b in zip(known, known[1:]):
    for k in range(a + 1, b):
        S_time[k] = S_time[a] + (S_time[b] - S_time[a]) * (k - a) / (b - a)
for i in range(1, len(S)):
    if S_time[i] < S_time[i - 1]:
        S_time[i] = S_time[i - 1]

SOFT, HARD = "，、：；", "。？！"
vis = lambda t: len(t.replace(" ", ""))

atoms, cur, cs = [], "", 0
for i, ch in enumerate(S):
    cur += ch
    if ch in SOFT or ch in HARD:
        atoms.append({"s": cs, "text": cur, "hard": ch in HARD})
        cur, cs = "", i + 1
if cur.strip():
    atoms.append({"s": cs, "text": cur, "hard": True})

# merge atoms into <=MAXLEN lines, never across a hard stop
lines, c = [], None
for a in atoms:
    if c is None:
        c = dict(a)
    elif c["hard"] or vis(c["text"] + a["text"]) > args.maxlen:
        lines.append(c); c = dict(a)
    else:
        c["text"] += a["text"]; c["hard"] = a["hard"]
if c:
    lines.append(c)

def tokenize(text, base):
    toks, i = [], 0
    while i < len(text):
        if re.match(r"[A-Za-z0-9]", text[i]):
            j = i
            while j < len(text) and re.match(r"[A-Za-z0-9.\-]", text[j]):
                j += 1
            toks.append((text[i:j], base + i)); i = j
        else:
            toks.append((text[i], base + i)); i += 1
    return toks

final = []
for ln in lines:
    if vis(ln["text"]) <= args.maxlen:
        final.append({"s": ln["s"], "text": ln["text"]}); continue
    pieces, cur, cst = [], "", None
    for tok, pos in tokenize(ln["text"], ln["s"]):
        tok_latin = bool(re.match(r"[A-Za-z0-9]", tok))
        st = cur.strip()
        last_cjk = bool(st) and not re.match(r"[A-Za-z0-9 ]", st[-1])
        early = tok_latin and last_cjk and vis(cur) >= args.maxlen - 8  # latin names off the tail
        if cur == "":
            cur, cst = tok, pos
        elif vis(cur + tok) > args.maxlen or early:
            pieces.append({"s": cst, "text": cur}); cur, cst = tok, pos
        else:
            cur += tok
    if cur.strip():
        pieces.append({"s": cst, "text": cur})
    if len(pieces) >= 2 and vis(pieces[-1]["text"]) <= 2:  # anti-orphan tail
        pieces[-2]["text"] += pieces[-1]["text"]; pieces.pop()
    final.extend(pieces)

caps = []
for ln in final:
    disp = ln["text"].strip().strip("，、：；。 ")
    if disp:
        caps.append({"t0": round(S_time[ln["s"]], 2), "text": disp})
for j in range(len(caps)):
    caps[j]["t1"] = round(caps[j + 1]["t0"], 2) if j + 1 < len(caps) else round(audio_end, 2)

print("// FORCED-ALIGNED: correct script text on whisper word timings (align_captions.py).")
print("export type Cap = { t0: number; t1: number; text: string };")
print(f"export const {args.const}: Cap[] = [")
for cp in caps:
    safe = cp["text"].replace("\\", "\\\\").replace("'", "\\'")
    print(f"  {{ t0: {cp['t0']}, t1: {cp['t1']}, text: '{safe}' }},")
print("];")

sys.stderr.write(f"# captions: {len(caps)}, longest: {max(vis(c['text']) for c in caps)} chars\n")
if args.anchors:
    anchors = [ln.strip() for ln in open(args.anchors) if ln.strip()]
    pos, frames = 0, [0]
    for anc in anchors:
        idx = S.find(anc, pos)
        if idx < 0:
            sys.stderr.write(f"!! anchor NOT FOUND (in order): {anc}\n"); idx = pos
        pos = idx + len(anc)
        frames.append(round(S_time[idx] * args.fps))
    total = round(audio_end * args.fps)
    durs = [frames[i + 1] - frames[i] for i in range(len(frames) - 1)] + [total - frames[-1]]
    sys.stderr.write(f"# SCENE START FRAMES: {frames}\n# SCENE DURATIONS: {durs}\n# TOTAL FRAMES: {total}\n")
# word-beat table: use these times to set each in-scene element's `at` (gotchas 坑10)
sys.stderr.write("\n# caption -> frame (element `at` beats):\n")
for cp in caps:
    sys.stderr.write(f"#  {round(cp['t0']*args.fps):>5}f  {cp['t0']:>7.2f}s  {cp['text']}\n")
