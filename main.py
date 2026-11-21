#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Draws an open passport spread of the Republic of Velmara -- a landlocked
mountain republic that does not exist -- as a single PNG written to
/output/entry.png.  Pure PIL: security-paper guilloche, coat of arms,
holder portrait, bilingual data page with a valid ICAO machine-readable
zone, and a visas page whose stamps agree with the data page.

Holder: Andrej V. Sorin of Veligrad.  Passport issued 03 JUN 2021 in
Veligrad; travel stamps (Dravania 2022, Ostrelia 2024, Dravania 2025)
all fall inside its validity.  The telling detail is the green
High-Pass Endorsement of the Warden of Passes -- a mountain country's
paperwork.
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

SS = 2                      # supersample factor
W, H = 1024, 730            # final size
CW, CH = W * SS, H * SS     # canvas size while drawing

FONT_DIR = "/usr/share/fonts/truetype"
SERIF = f"{FONT_DIR}/liberation/LiberationSerif-Regular.ttf"
SERIF_B = f"{FONT_DIR}/liberation/LiberationSerif-Bold.ttf"
SERIF_I = f"{FONT_DIR}/liberation/LiberationSerif-Italic.ttf"
SANS = f"{FONT_DIR}/liberation/LiberationSans-Regular.ttf"
SANS_B = f"{FONT_DIR}/liberation/LiberationSans-Bold.ttf"
MONO = f"{FONT_DIR}/liberation/LiberationMono-Regular.ttf"
MONO_B = f"{FONT_DIR}/liberation/LiberationMono-Bold.ttf"

_font_cache = {}


def F(path, size):
    """Font at `size` final pixels (scaled to the drawing canvas)."""
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, int(size * SS))
    return _font_cache[key]


# ---------------------------------------------------------------- colours
PAPER = (244, 238, 221)
PAPER_EDGE = (232, 224, 199)
INK = (26, 36, 62)            # document navy-black
LABEL = (92, 106, 132)        # small-print blue-grey
RULE = (150, 158, 175)
GUIL_A = (126, 163, 184)      # guilloche inks (used at low alpha)
GUIL_B = (158, 178, 146)
BLUE_STAMP = (38, 74, 148)
RED_STAMP = (168, 44, 44)
VIOLET_STAMP = (96, 62, 148)
GREEN_STAMP = (30, 110, 74)


def text_spaced(d, xy, s, font, fill, tracking=0, anchor_left=True):
    """Draw letter-spaced text; returns the total width in canvas px."""
    x, y = xy
    total = 0
    for ch in s:
        d.text((x + total, y), ch, font=font, fill=fill)
        total += d.textlength(ch, font=font) + tracking * SS
    return total - (tracking * SS if s else 0)


def text_w(d, s, font, tracking=0):
    return d.textlength(s, font=font) + tracking * SS * max(0, len(s) - 1)


def centered_spaced(d, cx, y, s, font, fill, tracking=0):
    w = text_w(d, s, font, tracking)
    text_spaced(d, (cx - w / 2, y), s, font, fill, tracking)
    return w


# ---------------------------------------------------------------- guilloche
def rosette(d, cx, cy, r_out, r_in, lobes, ink, alpha, width=1):
    """One hypotrochoid-style guilloche rosette."""
    pts = []
    steps = 720
    for i in range(steps + 1):
        t = 2 * math.pi * i / steps
        r = r_in + (r_out - r_in) * (0.5 + 0.5 * math.cos(lobes * t))
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    d.line(pts, fill=ink + (alpha,), width=max(1, int(width * SS / 2)))


def guilloche_layer(w, h):
    """Fine security pattern for one page, as an RGBA overlay."""
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # horizontal wave bands
    for row in range(0, h, int(13 * SS)):
        pts = []
        for x in range(0, w + 8, 8):
            y = row + 3.2 * SS * math.sin(x / (46 * SS) + row / (29 * SS))
            pts.append((x, y))
        d.line(pts, fill=GUIL_A + (26,), width=1)
    # rosettes in a loose grid, alternating inks
    cols = [int(f * w) for f in (0.18, 0.5, 0.82)]
    rows = [int(f * h) for f in (0.16, 0.5, 0.84)]
    for i, cx in enumerate(cols):
        for j, cy in enumerate(rows):
            ink = GUIL_A if (i + j) % 2 == 0 else GUIL_B
            for k, (ro, ri, lob) in enumerate(
                    ((86, 30, 9), (66, 24, 7), (46, 16, 11), (28, 10, 6))):
                rosette(d, cx, cy, ro * SS, ri * SS, lob, ink,
                        30 - 4 * k)
    return lay


# ---------------------------------------------------------------- arms
def draw_arms(d, cx, cy, s, alpha=255):
    """Coat of arms of Velmara: azure shield, three silver peaks,
    a gold star, and a wavy base for the River Sora.  `s` = height px (final)."""
    s = s * SS
    w = s * 0.78
    x0, x1 = cx * SS - w / 2, cx * SS + w / 2
    y0, y1 = cy * SS - s / 2, cy * SS + s / 2
    navy = (24, 52, 102, alpha)
    silver = (226, 230, 236, alpha)
    gold = (196, 152, 44, alpha)
    # shield outline: straight top/sides, pointed base
    shield = [(x0, y0), (x1, y0), (x1, y0 + s * 0.52),
              (cx * SS, y1), (x0, y0 + s * 0.52)]
    d.polygon(shield, fill=navy)
    # peaks (three triangles, snow-capped by the silver fill)
    base = y0 + s * 0.66
    peaks = [((x0 + w * 0.06), (cx * SS - w * 0.16), (cx * SS - w * 0.02)),
             ((cx * SS - w * 0.20), (cx * SS), (cx * SS + w * 0.20)),
             ((cx * SS + w * 0.02), (cx * SS + w * 0.16), (x1 - w * 0.06))]
    for lx, tx, rx in peaks:
        d.polygon([(lx, base), (tx, y0 + s * 0.34), (rx, base)], fill=silver)
    # wavy river at the base
    pts = []
    for i in range(41):
        x = x0 + w * 0.10 + (w * 0.80) * i / 40
        y = y0 + s * 0.76 + 2.2 * SS * math.sin(i / 40 * math.pi * 3)
        pts.append((x, y))
    d.line(pts, fill=(120, 178, 214, alpha), width=max(2, int(2.2 * SS)))
    # gold star above the peaks
    sx, sy, r = cx * SS, y0 + s * 0.17, s * 0.085
    star = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        star.append((sx + rr * math.cos(ang), sy + rr * math.sin(ang)))
    d.polygon(star, fill=gold)
    d.line(shield + [shield[0]], fill=(16, 34, 66, alpha),
           width=max(2, int(2 * SS)))


# ---------------------------------------------------------------- portrait
def draw_portrait(pw, ph):
    """Holder's photograph: a flat, softly shaded front portrait of a man
    in his late thirties, short brown hair, navy jacket.  pw/ph final px."""
    w, h = int(pw * SS), int(ph * SS)
    img = Image.new("RGB", (w, h), (206, 201, 188))
    d = ImageDraw.Draw(img)
    # backdrop: gentle vertical falloff + a faint guilloche ring behind head
    for yy in range(h):
        t = yy / h
        c = tuple(int(a + (b - a) * t) for a, b in
                  zip((216, 211, 198), (188, 182, 166)))
        d.line([(0, yy), (w, yy)], fill=c)
    for r in (0.62, 0.52, 0.43):
        d.ellipse([w / 2 - w * r, h * 0.40 - w * r, w / 2 + w * r,
                   h * 0.40 + w * r], outline=(170, 168, 152), width=2)
    skin = (201, 148, 108)
    skin_sh = (178, 124, 86)
    hair = (66, 46, 30)
    # shoulders / jacket
    d.polygon([(w * 0.06, h), (w * 0.16, h * 0.78), (w * 0.34, h * 0.70),
               (w * 0.66, h * 0.70), (w * 0.84, h * 0.78), (w * 0.94, h)],
              fill=(38, 44, 62))
    # shirt + tie
    d.polygon([(w * 0.40, h * 0.70), (w * 0.60, h * 0.70), (w * 0.545, h),
               (w * 0.455, h)], fill=(228, 228, 224))
    d.polygon([(w * 0.478, h * 0.72), (w * 0.522, h * 0.72), (w * 0.512, h),
               (w * 0.488, h)], fill=(96, 30, 38))
    # neck
    d.rectangle([w * 0.435, h * 0.56, w * 0.565, h * 0.72], fill=skin_sh)
    # ears
    d.ellipse([w * 0.265, h * 0.36, w * 0.325, h * 0.50], fill=skin)
    d.ellipse([w * 0.675, h * 0.36, w * 0.735, h * 0.50], fill=skin)
    # head
    d.ellipse([w * 0.315, h * 0.08, w * 0.685, h * 0.62], fill=skin)
    # jaw shading
    d.pieslice([w * 0.33, h * 0.10, w * 0.67, h * 0.635], 20, 160,
               fill=skin_sh)
    d.ellipse([w * 0.335, h * 0.085, w * 0.665, h * 0.60], fill=skin)
    # hair: cap with a straight hairline
    d.pieslice([w * 0.30, h * 0.025, w * 0.70, h * 0.44], 180, 360,
               fill=hair)
    d.rectangle([w * 0.295, h * 0.20, w * 0.325, h * 0.34], fill=hair)
    d.rectangle([w * 0.675, h * 0.20, w * 0.705, h * 0.34], fill=hair)
    # brows, eyes, nose, mouth -- kept minimal and even
    d.line([(w * 0.375, h * 0.335), (w * 0.455, h * 0.330)], fill=(70, 50, 34),
           width=int(2.4 * SS))
    d.line([(w * 0.545, h * 0.330), (w * 0.625, h * 0.335)], fill=(70, 50, 34),
           width=int(2.4 * SS))
    for ex in (0.415, 0.585):
        d.ellipse([w * (ex - 0.026), h * 0.362, w * (ex + 0.026), h * 0.388],
                  fill=(250, 248, 244))
        d.ellipse([w * (ex - 0.011), h * 0.366, w * (ex + 0.011), h * 0.386],
                  fill=(52, 40, 30))
    d.line([(w * 0.50, h * 0.40), (w * 0.488, h * 0.475), (w * 0.512, h * 0.478)],
           fill=skin_sh, width=int(1.8 * SS))
    d.line([(w * 0.435, h * 0.535), (w * 0.565, h * 0.535)], fill=(146, 92, 70),
           width=int(2.2 * SS))
    return img.filter(ImageFilter.GaussianBlur(1.1 * SS / 2))


# ---------------------------------------------------------------- stamps
def _ink_wear(lay, seed):
    """Knock random specks out of a stamp layer so the ink looks stamped."""
    rnd = random.Random(seed)
    w, h = lay.size
    noise = Image.effect_noise((w, h), 46).convert("L")
    noise = noise.point(lambda v: 255 if v > 96 else 150)
    r, g, b, a = lay.split()
    a = ImageChops.multiply(a, noise)
    return Image.merge("RGBA", (r, g, b, a))


def round_stamp(diameter, color, lines, seed):
    """Circular border stamp; lines = [(text, font, dy), ...] centred."""
    dpx = int(diameter * SS)
    pad = int(10 * SS)
    size = dpx + 2 * pad
    lay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    cx = cy = size / 2
    dr.ellipse([pad, pad, pad + dpx, pad + dpx], outline=color + (235,),
               width=int(3 * SS))
    dr.ellipse([pad + 5 * SS, pad + 5 * SS, pad + dpx - 5 * SS,
                pad + dpx - 5 * SS], outline=color + (235,),
               width=int(1.1 * SS))
    for txt, font, dy in lines:
        tw = dr.textlength(txt, font=font)
        dr.text((cx - tw / 2, cy + dy * SS), txt, font=font,
                fill=color + (235,))
    return _ink_wear(lay, seed)


def rect_stamp(w, h, color, lines, seed, double=True):
    """Rectangular border stamp; lines = [(text, font, dy), ...]."""
    pad = int(8 * SS)
    lay = Image.new("RGBA", (int(w * SS) + 2 * pad, int(h * SS) + 2 * pad),
                    (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    Wp, Hp = lay.size
    dr.rectangle([pad, pad, Wp - pad, Hp - pad], outline=color + (232,),
                 width=int(2.6 * SS))
    if double:
        o = int(4.5 * SS)
        dr.rectangle([pad + o, pad + o, Wp - pad - o, Hp - pad - o],
                     outline=color + (232,), width=int(1 * SS))
    for txt, font, dy in lines:
        tw = dr.textlength(txt, font=font)
        dr.text((Wp / 2 - tw / 2, Hp / 2 + dy * SS), txt, font=font,
                fill=color + (232,))
    return _ink_wear(lay, seed)


def place(base, layer, cx, cy, angle):
    rot = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    base.alpha_composite(rot, (int(cx * SS - rot.width / 2),
                               int(cy * SS - rot.height / 2)))


# ---------------------------------------------------------------- MRZ
def check_digit(s):
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(s):
        if ch.isdigit():
            v = int(ch)
        elif ch == "<":
            v = 0
        else:
            v = ord(ch) - 55          # A=10 .. Z=35
        total += v * weights[i % 3]
    return str(total % 10)


def build_mrz():
    doc = "VL0488217"
    dob, exp = "880314", "310603"
    personal = "8803147719<<<<"
    line2 = (doc + check_digit(doc) + "VLM" + dob + check_digit(dob) + "M"
             + exp + check_digit(exp) + personal + check_digit(personal))
    composite = line2[0:10] + line2[13:20] + line2[21:43]
    line2 = line2[:43] + check_digit(composite)
    line1 = "P<VLMSORIN<<ANDREJ<VIKTOR"
    line1 = line1 + "<" * (44 - len(line1))
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


# ---------------------------------------------------------------- fields
def field(d, x, y, label_en, label_vl, value, value_font=None, w=None):
    """One data field: bilingual small label, value, hair rule."""
    d.text((x * SS, y * SS), f"{label_en} / {label_vl}",
           font=F(SANS, 8.5), fill=LABEL)
    vf = value_font or F(SANS_B, 14.5)
    d.text((x * SS, (y + 12) * SS), value, font=vf, fill=INK)
    if w:
        d.line([(x * SS, (y + 33) * SS), ((x + w) * SS, (y + 33) * SS)],
               fill=RULE, width=max(1, int(0.7 * SS)))


def build():
    img = Image.new("RGBA", (CW, CH), PAPER + (255,))
    page_w = CW // 2

    # --- security paper on both pages
    for px in (0, page_w):
        img.alpha_composite(guilloche_layer(page_w, CH), (px, 0))
    d = ImageDraw.Draw(img, "RGBA")

    # --- page shading: gutter shadow + outer falloff
    for i in range(int(26 * SS)):
        a = int(52 * (1 - i / (26 * SS)))
        d.line([(page_w - i, 0), (page_w - i, CH)], fill=(60, 55, 40, a))
        d.line([(page_w + i, 0), (page_w + i, CH)], fill=(60, 55, 40, a))
    for i in range(int(10 * SS)):
        a = int(26 * (1 - i / (10 * SS)))
        d.line([(i, 0), (i, CH)], fill=(60, 55, 40, a))
        d.line([(CW - 1 - i, 0), (CW - 1 - i, CH)], fill=(60, 55, 40, a))
        d.line([(0, i), (CW, i)], fill=(60, 55, 40, a))
        d.line([(0, CH - 1 - i), (CW, CH - 1 - i)], fill=(60, 55, 40, a))

    M = 36                      # page margin (final px)
    LX1, LX2 = M, 512 - M       # left page text span
    RX1, RX2 = 512 + M, 1024 - M

    # ================================================================ LEFT
    # header: arms + country name + PASSPORT
    draw_arms(d, LX1 + 30, 52, 62)
    d.text(((LX1 + 72) * SS, 26 * SS), "REPUBLIC OF VELMARA",
           font=F(SERIF_B, 20), fill=INK)
    text_spaced(d, ((LX1 + 73) * SS, 52 * SS), "REPUBLIKA  VELMARSKA",
                F(SERIF, 11.5), LABEL, tracking=2.2)
    pw = text_w(d, "PASSPORT", F(SERIF_B, 15), tracking=1.5)
    text_spaced(d, (LX2 * SS - pw, 28 * SS), "PASSPORT", F(SERIF_B, 15),
                INK, tracking=1.5)
    pw2 = text_w(d, "PAS", F(SERIF, 10), tracking=1.5)
    text_spaced(d, (LX2 * SS - pw2, 50 * SS), "PAS", F(SERIF, 10),
                LABEL, tracking=1.5)
    d.line([(LX1 * SS, 88 * SS), (LX2 * SS, 88 * SS)], fill=INK,
           width=int(1.6 * SS))
    d.line([(LX1 * SS, 92 * SS), (LX2 * SS, 92 * SS)], fill=INK,
           width=int(0.7 * SS))

    # portrait + ghost image
    photo = draw_portrait(148, 188)
    img.paste(photo, (int(LX1 * SS), int(112 * SS)))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([LX1 * SS, 112 * SS, (LX1 + 148) * SS, (112 + 188) * SS],
                outline=(90, 90, 90), width=int(1.2 * SS))
    ghost = draw_portrait(60, 76).convert("RGBA")
    ghost.putalpha(52)
    img.paste(ghost, (int((LX2 - 60) * SS), int(464 * SS)), ghost)
    d = ImageDraw.Draw(img, "RGBA")

    # top row of the data block: type / code / number
    DX = LX1 + 168
    field(d, DX, 112, "Type", "Typ", "P", w=44)
    field(d, DX + 62, 112, "Code", "Kod", "VLM", w=52)
    field(d, DX + 132, 112, "Passport No", "Cislo pasu", "VL0488217",
          value_font=F(SANS_B, 15), w=112)

    field(d, DX, 158, "Surname", "Priezvisko", "SORIN", w=276)
    field(d, DX, 204, "Given names", "Mena", "ANDREJ VIKTOR", w=276)
    field(d, DX, 250, "Nationality", "Statna prislusnost", "VELMARIAN",
          w=170)
    field(d, DX + 186, 250, "Sex", "Pohlavie", "M", w=90)
    field(d, DX, 296, "Date of birth", "Datum narodzenia", "14 MAR 1988",
          w=170)
    field(d, DX + 186, 296, "Place of birth", "Miesto narodzenia",
          "VELIGRAD", w=90)

    # full-width lower fields
    field(d, LX1, 352, "Place of residence", "Bydlisko",
          "14 ULICA JAZERA, VELIGRAD", w=210)
    field(d, LX1 + 226, 352, "Height", "Vyska", "182 CM", w=86)
    field(d, LX1 + 328, 352, "Eyes", "Oci", "BROWN", w=112)
    field(d, LX1, 398, "Date of issue", "Datum vydania", "03 JUN 2021",
          w=150)
    field(d, LX1 + 166, 398, "Date of expiry", "Datum platnosti",
          "03 JUN 2031", w=150)
    field(d, LX1 + 332, 398, "Authority", "Vydal",
          "VELIGRAD", w=108)
    d.text((LX1 * SS, 446 * SS),
           "MINISTRY OF THE INTERIOR  ·  MINISTERSTVO VNUTRA",
           font=F(SANS, 9), fill=LABEL)

    # signature
    d.text(((LX1 + 4) * SS, 486 * SS), "Signature of holder / Podpis drzitela",
           font=F(SANS, 8.5), fill=LABEL)
    sig = Image.new("RGBA", (int(190 * SS), int(44 * SS)), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sig)
    sd.text((6 * SS, 4 * SS), "A. Sorin", font=F(SERIF_I, 27),
            fill=(24, 40, 96, 235))
    sig = sig.rotate(-3, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(sig, (int((LX1 + 8) * SS), int(500 * SS)))
    d = ImageDraw.Draw(img, "RGBA")
    d.line([(LX1 * SS, 546 * SS), ((LX1 + 200) * SS, 546 * SS)],
           fill=RULE, width=max(1, int(0.7 * SS)))
    d.text(((LX1 + 208) * SS, 506 * SS),
           "This passport contains 32 pages.", font=F(SERIF_I, 10.5),
           fill=LABEL)
    d.text(((LX1 + 208) * SS, 522 * SS),
           "Tento pas obsahuje 32 stran.", font=F(SERIF_I, 10.5),
           fill=LABEL)

    # perforated number down the outer edge
    perf = Image.new("RGBA", (int(180 * SS), int(16 * SS)), (0, 0, 0, 0))
    pd = ImageDraw.Draw(perf)
    text_spaced(pd, (0, 0), "VL0488217", F(MONO, 11), (110, 110, 110, 200),
                tracking=3)
    perf = perf.rotate(90, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(perf, (int(11 * SS), int(270 * SS)))
    d = ImageDraw.Draw(img, "RGBA")

    # machine-readable zone
    d.rectangle([LX1 * SS, 606 * SS, LX2 * SS, 716 * SS],
                fill=(250, 247, 238))
    d.line([(LX1 * SS, 606 * SS), (LX2 * SS, 606 * SS)], fill=RULE,
           width=max(1, int(0.7 * SS)))
    l1, l2 = build_mrz()
    mfont = F(MONO, 16.5)
    cw = d.textlength("M", font=mfont)
    x0 = (512 * SS - 44 * cw) / 2
    d.text((x0, 622 * SS), l1, font=mfont, fill=(20, 20, 20))
    d.text((x0, 664 * SS), l2, font=mfont, fill=(20, 20, 20))

    # ================================================================ RIGHT
    centered_spaced(d, (512 + 256) * SS, 30 * SS, "VISAS", F(SERIF_B, 15),
                    INK, tracking=4)
    centered_spaced(d, (512 + 256) * SS, 54 * SS, "VIZY", F(SERIF, 10.5),
                    LABEL, tracking=4)
    d.text(((RX2 - 14) * SS, 30 * SS), "4", font=F(SERIF, 11), fill=LABEL)
    d.line([(RX1 * SS, 88 * SS), (RX2 * SS, 88 * SS)], fill=INK,
           width=int(1.6 * SS))
    d.line([(RX1 * SS, 92 * SS), (RX2 * SS, 92 * SS)], fill=INK,
           width=int(0.7 * SS))

    # faint watermark arms in the middle of the visas page
    wm = Image.new("RGBA", (int(300 * SS), int(300 * SS)), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wm)
    draw_arms(wd, 150, 150, 210, alpha=21)
    img.alpha_composite(wm, (int((512 + 106) * SS), int(215 * SS)))
    d = ImageDraw.Draw(img, "RGBA")

    f_country = F(SANS_B, 13)
    f_mid = F(SANS, 10.5)
    f_date = F(SANS_B, 15)
    f_small = F(SANS, 8.5)

    # -- the telling detail: High-Pass Endorsement, issued with the passport
    endorse = rect_stamp(252, 96, GREEN_STAMP, [
        ("REPUBLIC OF VELMARA — WARDEN OF PASSES", F(SANS_B, 10), -40),
        ("HIGH-PASS ENDORSEMENT", F(SANS_B, 12.5), -22),
        ("Guide required above 3,000 m", f_mid, -2),
        ("Fee paid 40 kruna · Veligrad 03 JUN 2021", f_small, 14),
        ("No. HP-2214", f_small, 28),
    ], seed=11)
    place(img, endorse, 512 + 150, 152, -3)

    # -- Dravania, September 2022 (arrival + departure, Korvat airport)
    arr22 = round_stamp(118, BLUE_STAMP, [
        ("DRAVANIA", f_country, -44),
        ("KORVAT INTL AIRPORT", f_small, -24),
        ("ARRIVED", F(SANS_B, 11), -6),
        ("17 SEP 2022", f_date, 10),
    ], seed=22)
    place(img, arr22, 512 + 330, 168, 7)
    dep22 = round_stamp(104, BLUE_STAMP, [
        ("DRAVANIA", f_country, -38),
        ("KORVAT INTL AIRPORT", f_small, -19),
        ("DEPARTED", F(SANS_B, 11), -3),
        ("24 SEP 2022", F(SANS_B, 13.5), 12),
    ], seed=23)
    place(img, dep22, 512 + 408, 268, -10)

    # -- Ostrelia, May 2024 (rectangular border stamps, Vessen North Gate)
    arr24 = rect_stamp(196, 84, RED_STAMP, [
        ("OSTRELIA — VESSEN NORTH GATE", F(SANS_B, 10.5), -32),
        ("ADMITTED", F(SANS_B, 12), -13),
        ("02 MAY 2024", f_date, 4),
        ("Class V · 90 days", f_small, 22),
    ], seed=31)
    place(img, arr24, 512 + 140, 330, -6)
    dep24 = rect_stamp(196, 84, RED_STAMP, [
        ("OSTRELIA — VESSEN NORTH GATE", F(SANS_B, 10.5), -32),
        ("DEPARTED", F(SANS_B, 12), -13),
        ("09 MAY 2024", f_date, 4),
        ("Exit 14", f_small, 22),
    ], seed=32)
    place(img, dep24, 512 + 368, 392, 4)

    # -- Dravania again, January 2025 (violet pair, smaller)
    arr25 = round_stamp(104, VIOLET_STAMP, [
        ("DRAVANIA", f_country, -38),
        ("KORVAT INTL AIRPORT", f_small, -19),
        ("ARRIVED", F(SANS_B, 11), -3),
        ("11 JAN 2025", F(SANS_B, 13.5), 12),
    ], seed=41)
    place(img, arr25, 512 + 128, 492, -13)
    dep25 = round_stamp(104, VIOLET_STAMP, [
        ("DRAVANIA", f_country, -38),
        ("KORVAT INTL AIRPORT", f_small, -19),
        ("DEPARTED", F(SANS_B, 11), -3),
        ("19 JAN 2025", F(SANS_B, 13.5), 12),
    ], seed=42)
    place(img, dep25, 512 + 262, 540, 9)

    # a border officer's handwritten annotation beside the 2025 arrival
    note = Image.new("RGBA", (int(200 * SS), int(30 * SS)), (0, 0, 0, 0))
    nd = ImageDraw.Draw(note)
    nd.text((2 * SS, 2 * SS), "seen — passes in order",
            font=F(SERIF_I, 13), fill=(30, 50, 120, 190))
    note = note.rotate(-6, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(note, (int((512 + 282) * SS), int(618 * SS)))
    d = ImageDraw.Draw(img, "RGBA")

    d.text((RX1 * SS, 668 * SS),
           "Endorsements and stamps must not predate the date of issue.",
           font=F(SERIF_I, 10), fill=LABEL)
    d.text((RX1 * SS, 684 * SS),
           "Zapisy a peciatky nesmu predchadzat datum vydania.",
           font=F(SERIF_I, 10), fill=LABEL)

    # --- print texture: a whisper of grain so the paper is not digital-flat
    img = img.convert("RGB")
    grain = Image.effect_noise((CW, CH), 9).convert("L")
    grain = grain.point(lambda v: 246 + (v - 128) // 14)
    img = ImageChops.multiply(img, grain.convert("RGB"))

    img = img.resize((W, H), Image.LANCZOS)
    return img


def main():
    out_dir = "/output"
    os.makedirs(out_dir, exist_ok=True)
    img = build()
    path = os.path.join(out_dir, "entry.png")
    img.save(path, format="PNG", optimize=True)
    return path


if __name__ == "__main__":
    main()
