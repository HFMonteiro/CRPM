from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

base = Path('ARTIGO 3/agent_results')
fig_dir = base / 'figures'
fig_dir.mkdir(parents=True, exist_ok=True)
pre_path = Path('agent_results/pre_2024/cohort_FULLdata/visuals/dfg_pre_2024_cohort_incident_365d_FULLdata.png')
post_path = Path('agent_results/post_2024/cohort_FULLdata/visuals/dfg_post_2024_cohort_incident_365d_FULLdata.png')

pre = Image.open(pre_path).convert('RGBA')
post = Image.open(post_path).convert('RGBA')

# Target figure
dpi = 300
width_px = 1200
height_px = 800
canvas = Image.new('RGBA', (width_px, height_px), 'white')

# Layout margins
pad = 30
col_gap = 20
avail_w = width_px - 2*pad - col_gap
avail_h = height_px - 2*pad - 60  # leave space for titles
panel_w = avail_w // 2
panel_h = avail_h

# Helper to scale image to fit panel
def fit(img, max_w, max_h):
    w, h = img.size
    scale = min(max_w / w, max_h / h)
    return img.resize((max(1, int(w*scale)), max(1, int(h*scale))), Image.LANCZOS)

pre_fit = fit(pre, panel_w, panel_h)
post_fit = fit(post, panel_w, panel_h)

# Paste PRE
x1 = pad
y1 = pad + 40
canvas.paste(pre_fit, (x1 + (panel_w - pre_fit.width)//2, y1 + (panel_h - pre_fit.height)//2), pre_fit)

# Paste POST
x2 = pad + panel_w + col_gap
y2 = pad + 40
canvas.paste(post_fit, (x2 + (panel_w - post_fit.width)//2, y2 + (panel_h - post_fit.height)//2), post_fit)

# Draw titles using default font
try:
    font_title = ImageFont.truetype('arial.ttf', 22)
    font_suptitle = ImageFont.truetype('arial.ttf', 26)
except Exception:
    font_title = ImageFont.load_default()
    font_suptitle = ImageFont.load_default()

draw = ImageDraw.Draw(canvas)

draw.text((x1, pad), 'PRE (2022-2023): Directly-Follows Graph', fill='black', font=font_title)
draw.text((x2, pad), 'POST (2024-2025): Directly-Follows Graph', fill='black', font=font_title)

suptitle = 'DFG Comparison (Pipeline B · 365-day incident cohorts)'
sz = draw.textbbox((0,0), suptitle, font=font_suptitle)
draw.text(((width_px - (sz[2]-sz[0]))//2, 4), suptitle, fill='black', font=font_suptitle)

out = fig_dir / 'fig1_dfg_comparison.png'
canvas.convert('RGB').save(out, dpi=(dpi, dpi))
print('Saved', out)
