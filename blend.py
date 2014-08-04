import sys

import numpy
import PIL.Image

paths = sys.argv[1:]

size = None
arraysum = None

for path in paths:
    image = PIL.Image.open(path)
    if size is None:
        size = image.size
    else:
        assert size == image.size
    array = numpy.asarray(image, numpy.uint16)
    if arraysum is None:
        arraysum = array
    else:
        arraysum += array
arraysum /= len(paths)
image = PIL.Image.fromarray(numpy.asarray(arraysum, numpy.uint8))
image.save('output.jpg', quality=95)
