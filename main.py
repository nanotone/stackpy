import Queue
import sys
import threading
import Tkinter as tk

import numpy
import PIL.Image, PIL.ImageTk

paths = sys.argv[1:]

class AlignmentApp(object):
    def __init__(self):
        self.queue = Queue.Queue()

        self.root = tk.Tk()
        frame = tk.Frame(self.root, borderwidth=5)
        frame.pack()

        self.text = tk.Label(frame)
        self.text.pack()
        self.label = tk.Label(frame, borderwidth=0)
        self.label.bind('<Button-1>', self.clicked)
        self.next_photo()

    def load_photo(self):
        self.image = PIL.Image.open(paths[0])
        del paths[0]
        size = self.image.size
        self.scale = min(1024.0 / size[0], 768.0 / size[1])
        if self.scale < 1.0:
            new_size = tuple(int(round(s * self.scale)) for s in size)
            resized = self.image.resize(new_size)
        else:
            resized = self.image
        self.queue.put(resized)

    def process_queue(self):
        try:
            image = self.queue.get(block=False)
            self.label['image'] = self.label.image = PIL.ImageTk.PhotoImage(image)
            self.label.pack()
            self.text['text'] = 'click on a prominent star'
            self.clicks = []
            self.root.update_idletasks()
        except Queue.Empty:
            self.root.after(100, self.process_queue)

    def next_photo(self):
        self.text['text'] = 'loading next photo...'
        threading.Thread(target=self.load_photo).start()
        self.root.update_idletasks()
        self.root.after(100, self.process_queue)

    def clicked(self, event):
        loc = [int(round(e / self.scale)) for e in (event.x, event.y)]
        self.clicks.append(loc)
        cropped = self.image.crop((loc[0] - 30, loc[1] - 30, loc[0] + 30, loc[1] + 30))
        cropped = cropped.convert(mode='L')
        thresh = sum(cropped.getextrema()) / 2
        cropped = cropped.point([0 if i < thresh else i for i in xrange(256)])

        arr = numpy.asarray(cropped)
        arrsum = float(arr.sum())
        range60 = numpy.arange(60)
        center = [loc[i] - 30 + int(round((arr.sum(axis=i) * range60).sum() / arrsum)) for i in (0, 1)]
        print center
        if len(self.clicks) == 1:
            self.text['text'] = 'click on another prominent star'
        elif paths:
            self.next_photo()
        else:
            self.root.quit()

    def run(self):
        self.root.wm_attributes('-topmost', 1)
        self.root.mainloop()

AlignmentApp().run()
