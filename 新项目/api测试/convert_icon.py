from PIL import Image
import sys

in_path = r'D:\Desktop\OIP.jfif'
out_path = r'D:\Desktop\OIP.ico'

try:
    img = Image.open(in_path)
    if img.mode not in ('RGBA','RGB'):
        img = img.convert('RGBA')
    img.save(out_path, format='ICO', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
    print('saved', out_path)
except Exception as e:
    print('error', e)
    sys.exit(1)
