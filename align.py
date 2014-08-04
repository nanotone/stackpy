import math
import Queue
import sys
import threading
import Tkinter as tk

import numpy
import PIL.Image, PIL.ImageTk

paths = sys.argv[1:]
npics = len(paths)

class AlignmentApp(object):
    def __init__(self):
        self.queue = Queue.Queue()
        self.results = []

        self.root = tk.Tk()
        frame = tk.Frame(self.root, borderwidth=5)
        frame.pack()

        self.text = tk.Label(frame)
        self.text.pack()
        self.label = tk.Label(frame, borderwidth=0)
        self.label.bind('<Button-1>', self.clicked)
        self.next_photo()

    def load_photo(self):
        path = paths.pop(0)
        image = PIL.Image.open(path)
        size = image.size
        scale = min(1024.0 / size[0], 768.0 / size[1])
        if scale < 1.0:
            new_size = tuple(int(round(s * scale)) for s in size)
            resized = image.resize(new_size, resample=PIL.Image.BILINEAR)
        else:
            resized = image
            scale = 1.0
        self.queue.put({
            'orig': image,
            'path': path,
            'resized': resized,
            'scale': scale,
            'size': size,
        })

    def process_queue(self):
        try:
            pic = self.pic = self.queue.get(block=False)
            pic['anchors'] = []
            self.label['image'] = self.label.image = PIL.ImageTk.PhotoImage(pic['resized'])
            self.label.pack()
            self.text['text'] = 'click on a prominent star'
            self.root.update_idletasks()
        except Queue.Empty:
            self.root.after(100, self.process_queue)

    def next_photo(self):
        self.text['text'] = 'loading next photo...'
        threading.Thread(target=self.load_photo).start()
        self.root.update_idletasks()
        self.root.after(100, self.process_queue)

    def clicked(self, event):
        pic = self.pic
        loc = [int(round(e / pic['scale'])) for e in (event.x, event.y)]
        cropped = pic['orig'].crop((loc[0] - 30, loc[1] - 30, loc[0] + 30, loc[1] + 30))
        cropped = cropped.convert(mode='L')
        thresh = sum(cropped.getextrema()) / 2
        cropped = cropped.point([0 if i < thresh else i for i in xrange(256)])

        arr = numpy.asarray(cropped)
        arrsum = float(arr.sum())
        range60 = numpy.arange(60)
        center = [loc[axis] - 30 + int(round((arr.sum(axis=axis) * range60).sum() / arrsum)) for axis in (0, 1)]
        pic['anchors'].append(center)
        if len(pic['anchors']) == 1:
            self.text['text'] = 'click on another prominent star'
        else:
            del pic['orig']  # gc
            self.results.append(pic)
            if paths:
                self.next_photo()
            else:
                self.root.quit()

    def run(self):
        self.root.wm_attributes('-topmost', 1)
        self.root.mainloop()
        return self.results

pics = AlignmentApp().run()
if len(pics) != npics:
    raise Exception('alignment aborted')
for p in pics:
    a = p['anchors']
    p['theta'] = math.atan2(a[1][1] - a[0][1], a[1][0] - a[0][0])
    p['midpoint'] = ((a[0][0] + a[1][0]) * 0.5, (a[0][1] + a[1][1]) * 0.5)
avg_theta = sum(p['theta'] for p in pics) / len(pics)  # ignore wrapping
mid_result = min(pics, key=lambda p: abs(p['theta'] - avg_theta))
for p in pics:
    if p is mid_result:
        p['offset'] = (0, 0)
        p['offset2'] = p['size']
    p['dtheta'] = p['theta'] - mid_result['theta']
    (cos, sin) = math.cos(-p['dtheta']), math.sin(-p['dtheta'])  # N.B.: ccw rotation is backwards in img coords

    pt = [p['midpoint'][axis] - p['size'][axis] * 0.5 for axis in (0, 1)] # translate center to (0, 0)
    pt = (pt[0] * cos - pt[1] * sin,  # rotate
          pt[0] * sin + pt[1] * cos)
    p['midpoint'] = [pt[axis] + p['size'][axis] * 0.5 for axis in (0, 1)] # translate back
    p['t-l'] = [int(round(mid_result['midpoint'][axis] - p['midpoint'][axis])) for axis in (0, 1)]
    p['b-r'] = [p['t-l'][axis] + p['size'][axis] for axis in (0, 1)]
t_l = [max(p['t-l'][axis] for p in pics) for axis in (0, 1)]
b_r = [min(p['b-r'][axis] for p in pics) for axis in (0, 1)]
for p in pics:
    image = PIL.Image.open(p['path'])
    print "loading", p['path']
    image.putpixel(tuple(p['anchors'][0]), (255, 0, 0))
    image.putpixel(tuple(p['anchors'][1]), (255, 0, 0))
    if p is not mid_result:
        angle = p['dtheta'] * 180 / math.pi
        image = image.rotate(angle, resample=PIL.Image.BILINEAR)
    box = (
        t_l[0] - p['t-l'][0],
        t_l[1] - p['t-l'][1],
        b_r[0] - p['t-l'][0],
        b_r[1] - p['t-l'][1],
    )
    image = image.crop(box)
    image.save(p['path'] + '-aligned.png')
