"""Assemble a labelled preview from actual lossless browser exports, not a new rendering."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path('docs/rotation-validation/visual');out=Image.new('RGB',(900,850),'#101010');draw=ImageDraw.Draw(out)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',16);small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',12)
draw.text((20,16),'Split vectorscopes + TwinPeaks',font=font,fill='#ddd');draw.text((20,42),'Actual lossless browser scope captures · synthetic RGB waves · BT.709',font=small,fill='#999')
for i,(scope,title) in enumerate([(4,'LOWS · Y′ < 0.25'),(5,'MIDS · 0.25 ≤ Y′ < 0.75'),(6,'HIGHS · Y′ ≥ 0.75')]):
    im=Image.open(root/f'sine-{scope}-overlay.png').convert('RGB');im=im.resize((240,240),Image.Resampling.NEAREST);out.paste(im,(i*300+30,110));draw.text((i*300+30,80),title,font=small,fill='#bbb');draw.text((i*300+30,360),'Cb / Cr · same scale ±0.5',font=small,fill='#888')
draw.line((20,400,880,400),fill='#444');draw.text((20,420),'TWINPEAKS · left G′ / R′ · right G′ / B′',font=small,fill='#bbb')
im=Image.open(root/'sine-7-overlay.png').convert('RGB');im=im.resize((720,360),Image.Resampling.NEAREST);out.paste(im,(90,455));draw.text((20,822),'Preview enlarged with nearest-neighbour sampling. Validation uses the original captured pixels.',font=small,fill='#888');out.save('docs/rotation-validation/preview.png')
