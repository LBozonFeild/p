from lib import *
fn,pg=sys.argv[1],int(sys.argv[2])
doc=fitz.open(os.path.join(SRC,fn))
page=doc[pg-1]
print(page.rect, len(page.get_drawings()), len(page.get_images()))
for r in page_rows(page)[:int(sys.argv[3]) if len(sys.argv)>3 else 40]:
    print(f"{r['y0']:6.1f} x{r['x0']:5.1f} sz{r['size']:4.1f} {'B' if r['bold0'] else ' '} | {r['text'][:110]}")
