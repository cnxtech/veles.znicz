"""
Created on Aug 20, 2013

ImageSaver unit.

@author: Kazantsev Alexey <a.kazantsev@samsung.com>
"""
import numpy
import units
import scipy.misc
import os
import glob
import error


class ImageSaver(units.Unit):
    """Saves input to pngs in the supplied directory.

    Will remove all existing png files in the supplied directory.

    Attributes:
        out_dirs: output directories by minibatch_class where to save png.
        input: batch with input samples.
        output: batch with corresponding output samples (may be None).
        target: batch with corresponding target samples (may be None).
        indexes: sample indexes.
        labels: sample labels.
        max_idx: indexes of element with maximum value for each sample.

    Remarks:
        if max_idx != None:
            Softmax classifier is assumed and only failed samples
            will be saved.
        else:
            MSE task is assumed and output and target
            should be None or not None both simultaneously.
    """
    def __init__(self, out_dirs=[".", ".", "."]):
        super(ImageSaver, self).__init__()
        self.out_dirs = out_dirs
        self.input = None  # formats.Vector()
        self.output = None  # formats.Vector()
        self.target = None  # formats.Vector()
        self.indexes = None  # formats.Vector()
        self.labels = None  # formats.Vector()
        self.max_idx = None  # formats.Vector()
        self.minibatch_class = None  # [0]
        self.minibatch_size = None  # [0]
        self.this_save_time = [0]
        self.last_save_time = 0

    def as_image(self, x):
        if len(x.shape) == 2:
            return x.reshape(x.shape[0], x.shape[1], 1)
        if len(x.shape) == 3:
            if x.shape[2] == 3:
                return x
            if x.shape[0] == 3:
                xx = numpy.empty([x.shape[1], x.shape[2], 3],
                                 dtype=x.dtype)
                xx[:, :, 0:1] = x[0:1, :, :].reshape(
                    x.shape[1], x.shape[2], 1)[:, :, 0:1]
                xx[:, :, 1:2] = x[1:2, :, :].reshape(
                    x.shape[1], x.shape[2], 1)[:, :, 0:1]
                xx[:, :, 2:3] = x[2:3, :, :].reshape(
                    x.shape[1], x.shape[2], 1)[:, :, 0:1]
                return xx
        raise error.ErrBadFormat("Unsupported input shape: %s" % (
                                                        str(x.shape)))

    def run(self):
        self.input.sync()
        if self.output != None:
            self.output.sync()
        self.indexes.sync()
        self.labels.sync()
        if self.last_save_time < self.this_save_time[0]:
            self.last_save_time = self.this_save_time[0]
            for dirnme in self.out_dirs:
                i = 0
                while True:
                    j = dirnme.find("/", i)
                    if j <= i:
                        break
                    try:
                        os.mkdir(dirnme[:j - 1])
                    except OSError:
                        pass
                    i = j + 1
                files = glob.glob("%s/*.png" % (dirnme))
                for file in files:
                    try:
                        os.unlink(file)
                    except OSError:
                        pass
        xyt = None
        x = None
        y = None
        t = None
        im = 0
        for i in range(0, self.minibatch_size[0]):
            x = self.as_image(self.input.v[i])
            idx = self.indexes.v[i]
            lbl = self.labels.v[i]
            if self.max_idx != None:
                im = self.max_idx[i]
                if im == lbl:
                    continue
                y = self.output.v[i]
            if (self.max_idx == None and
                self.output != None and self.target != None):
                y = self.as_image(self.output.v[i])
                t = self.as_image(self.target.v[i])
                y = y.reshape(t.shape)
            if self.max_idx == None and y != None:
                mse = numpy.linalg.norm(t - y) / x.size
            if xyt == None:
                n_rows = x.shape[0]
                n_cols = x.shape[1]
                if self.max_idx == None and y != None:
                    n_rows += y.shape[0]
                    n_cols = max(n_cols, y.shape[1])
                if self.max_idx == None and t != x:
                    n_rows += t.shape[0]
                    n_cols = max(n_cols, t.shape[1])
                xyt = numpy.empty([n_rows, n_cols, x.shape[2]], dtype=x.dtype)
            xyt[:] = 0
            offs = (xyt.shape[1] - x.shape[1]) >> 1
            xyt[:x.shape[0], offs:offs + x.shape[1]] = x[:, :]
            img = xyt[:x.shape[0], offs:offs + x.shape[1]]
            img *= -1.0
            img += 1.0
            img *= 127.5
            numpy.clip(img, 0, 255, img)
            if self.max_idx == None and y != None:
                offs = (xyt.shape[1] - y.shape[1]) >> 1
                xyt[x.shape[0]:x.shape[0] + y.shape[0],
                    offs:offs + y.shape[1]] = y[:, :]
                img = xyt[x.shape[0]:x.shape[0] + y.shape[0],
                          offs:offs + y.shape[1]]
                img *= -1.0
                img += 1.0
                img *= 127.5
                numpy.clip(img, 0, 255, img)
            if self.max_idx == None and t != x:
                offs = (xyt.shape[1] - t.shape[1]) >> 1
                xyt[x.shape[0] + y.shape[0]:, offs:offs + t.shape[1]] = t[:, :]
                img = xyt[x.shape[0] + y.shape[0]:, offs:offs + t.shape[1]]
                img *= -1.0
                img += 1.0
                img *= 127.5
                numpy.clip(img, 0, 255, img)
            if self.max_idx == None:
                fnme = "%s/%.6f_%d_%d.png" % (
                    self.out_dirs[self.minibatch_class[0]], mse, lbl, idx)
            else:
                fnme = "%s/%d_as_%d.%.0fpt.%d.png" % (
                    self.out_dirs[self.minibatch_class[0]], lbl, im, y[im],
                    idx)
            img = xyt
            if img.shape[2] == 1:
                img = img.reshape(img.shape[0], img.shape[1])
            scipy.misc.imsave(fnme, img.astype(numpy.uint8))
