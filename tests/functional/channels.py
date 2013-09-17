#!/usr/bin/python3.3 -O
"""
Created on Jul 3, 2013

File for channels recognition.

@author: Kazantsev Alexey <a.kazantsev@samsung.com>
"""
import sys
import os
import logging


def add_path(path):
    if path not in sys.path:
        sys.path.append(path)


this_dir = os.path.dirname(__file__)
if not this_dir:
    this_dir = "."
add_path("%s" % (this_dir))
add_path("%s/../.." % (this_dir))
add_path("%s/../../../src" % (this_dir))


import units
import formats
import numpy
import config
import rnd
import opencl
import plotters
import glob
import pickle
import scipy.ndimage
import tv_channel_plotter
import loader
import decision
import image_saver
import all2all
import evaluator
import gd
import re


class Loader(loader.ImageLoader):
    """Loads channels.

    Attributes:
        lbl_re_: regular expression for extracting label from filename.
    """
    def init_unpickled(self):
        super(Loader, self).init_unpickled()
        self.lbl_re_ = re.compile("/(\d+)\.\w+/[\w.]+$")

    def get_label_from_filename(self, filename):
        res = self.lbl_re_.search(filename)
        if res == None:
            return
        lbl = int(res.group(1))
        return lbl


class Workflow(units.OpenCLUnit):
    """Sample workflow.

    Attributes:
        start_point: start point.
        rpt: repeater.
        loader: loader.
        forward: list of all-to-all forward units.
        ev: evaluator softmax.
        stat: stat collector.
        decision: Decision.
        gd: list of gradient descent units.
    """
    def __init__(self, layers=None, device=None):
        super(Workflow, self).__init__(device=device)
        self.start_point = units.Unit()

        self.rpt = units.Repeater()
        self.rpt.link_from(self.start_point)

        train_paths = glob.glob("%s/channels/demo/img/*" % (
                                config.test_dataset_root,))
        train_paths.sort()
        for i in range(0, len(train_paths)):
            train_paths[i] += "/*.png"
        self.loader = Loader(train_paths=train_paths)
        self.loader.link_from(self.rpt)

        # Add forward units
        self.forward = []
        for i in range(0, len(layers)):
            if i < len(layers) - 1:
                aa = all2all.All2AllTanh([layers[i]], device=device)
            else:
                aa = all2all.All2AllSoftmax([layers[i]], device=device)
            self.forward.append(aa)
            if i:
                self.forward[i].link_from(self.forward[i - 1])
                self.forward[i].input = self.forward[i - 1].output
            else:
                self.forward[i].link_from(self.loader)
                self.forward[i].input = self.loader.minibatch_data

        # Add Image Saver unit
        self.image_saver = image_saver.ImageSaver(out_dirs=[
            "/data/veles/channels/demo/tmpimg/test",
            "/data/veles/channels/demo/tmpimg/validation",
            "/data/veles/channels/demo/tmpimg/train"])
        self.image_saver.link_from(self.forward[-1])
        self.image_saver.input = self.loader.minibatch_data
        self.image_saver.output = self.forward[-1].output
        self.image_saver.max_idx = self.forward[-1].max_idx
        self.image_saver.indexes = self.loader.minibatch_indexes
        self.image_saver.labels = self.loader.minibatch_labels
        self.image_saver.minibatch_class = self.loader.minibatch_class
        self.image_saver.minibatch_size = self.loader.minibatch_size

        # Add evaluator for single minibatch
        self.ev = evaluator.EvaluatorSoftmax(device=device)
        self.ev.link_from(self.image_saver)
        self.ev.y = self.forward[-1].output
        self.ev.batch_size = self.loader.minibatch_size
        self.ev.labels = self.loader.minibatch_labels
        self.ev.max_idx = self.forward[-1].max_idx
        self.ev.max_samples_per_epoch = self.loader.total_samples

        # Add decision unit
        self.decision = decision.Decision(snapshot_prefix="channels")
        self.decision.link_from(self.ev)
        self.decision.minibatch_class = self.loader.minibatch_class
        self.decision.minibatch_last = self.loader.minibatch_last
        self.decision.minibatch_n_err = self.ev.n_err_skipped
        self.decision.minibatch_confusion_matrix = self.ev.confusion_matrix
        self.decision.class_samples = self.loader.class_samples
        self.decision.workflow = self

        self.image_saver.gate_skip = [0]  # self.decision.just_snapshotted
        self.image_saver.gate_skip_not = [1]
        self.image_saver.snapshot_time = self.decision.snapshot_time

        # Add gradient descent units
        self.gd = list(None for i in range(0, len(self.forward)))
        self.gd[-1] = gd.GDSM(device=device)
        self.gd[-1].link_from(self.decision)
        self.gd[-1].err_y = self.ev.err_y
        self.gd[-1].y = self.forward[-1].output
        self.gd[-1].h = self.forward[-1].input
        self.gd[-1].weights = self.forward[-1].weights
        self.gd[-1].bias = self.forward[-1].bias
        self.gd[-1].gate_skip = self.decision.gd_skip
        self.gd[-1].batch_size = self.loader.minibatch_size
        for i in range(len(self.forward) - 2, -1, -1):
            self.gd[i] = gd.GDTanh(device=device)
            self.gd[i].link_from(self.gd[i + 1])
            self.gd[i].err_y = self.gd[i + 1].err_h
            self.gd[i].y = self.forward[i].output
            self.gd[i].h = self.forward[i].input
            self.gd[i].weights = self.forward[i].weights
            self.gd[i].bias = self.forward[i].bias
            self.gd[i].gate_skip = self.decision.gd_skip
            self.gd[i].batch_size = self.loader.minibatch_size
        self.rpt.link_from(self.gd[0])

        self.end_point = units.EndPoint()
        self.end_point.link_from(self.decision)
        self.end_point.gate_block = self.decision.complete
        self.end_point.gate_block_not = [1]

        self.loader.gate_block = self.decision.complete

        # Error plotter
        self.plt = []
        styles = ["r-", "b-", "k-"]
        for i in range(0, 3):
            self.plt.append(plotters.SimplePlotter(figure_label="num errors",
                                                   plot_style=styles[i]))
            self.plt[-1].input = self.decision.epoch_n_err_pt
            self.plt[-1].input_field = i
            self.plt[-1].link_from(self.decision)
            self.plt[-1].gate_block = self.decision.epoch_ended
            self.plt[-1].gate_block_not = [1]
        # Matrix plotter
        # """
        self.decision.vectors_to_sync[self.gd[0].weights] = 1
        self.plt_w = plotters.Weights2D(figure_label="First Layer Weights")
        self.plt_w.input = self.gd[0].weights
        self.plt_w.get_shape_from = self.forward[0].input
        self.plt_w.input_field = "v"
        self.plt_w.link_from(self.decision)
        self.plt_w.gate_block = self.decision.epoch_ended
        self.plt_w.gate_block_not = [1]
        # """
        # Confusion matrix plotter
        self.plt_mx = []
        for i in range(0, len(self.decision.confusion_matrixes)):
            self.plt_mx.append(plotters.MatrixPlotter(
                figure_label=(("Test", "Validation", "Train")[i] + " matrix")))
            self.plt_mx[-1].input = self.decision.confusion_matrixes
            self.plt_mx[-1].input_field = i
            self.plt_mx[-1].link_from(self.plt[-1])
            self.plt_mx[-1].gate_block = self.decision.epoch_ended
            self.plt_mx[-1].gate_block_not = [1]

    def initialize(self, threshold, threshold_low,
                   global_alpha, global_lambda,
                   minibatch_maxsize, device):
        self.loader.minibatch_maxsize[0] = minibatch_maxsize
        self.ev.device = device
        self.ev.threshold = threshold
        self.ev.threshold_low = threshold_low
        for gd in self.gd:
            gd.device = device
            gd.global_alpha = global_alpha
            gd.global_lambda = global_lambda
        for forward in self.forward:
            forward.device = device

        # If channels.feed is found - do only forward propagation.
        try:
            # feed = open("/tmp/feed", "rb")
            self.log().info("will open pipe")
            f = os.open("/tmp/feed", os.O_RDONLY)
            self.log().info("pipe opened")
            feed = os.fdopen(f, "rb")
            self.log().info("pipe linked to python descriptor")
            self.switch_to_forward_workflow(feed)
        except FileNotFoundError:
            self.log().info("pipe was not found")

        retval = self.start_point.initialize_dependent()
        if retval:
            return retval

    def run(self):
        retval = self.start_point.run_dependent()
        if retval:
            return retval
        self.end_point.wait()

    def switch_to_forward_workflow(self, feed):
        self.start_point.unlink()
        self.end_point.unlink()
        self.decision.unlink()
        self.ev.unlink()
        self.loader.unlink()
        self.rpt.unlink()
        for gd in self.gd:
            gd.unlink()
        self.image_saver.unlink()
        self.plt_w.unlink()
        for plt in self.plt:
            plt.unlink()
        for plt_mx in self.plt_mx:
            plt_mx.unlink()
        for forward in self.forward:
            forward.unlink()
        self.rpt.link_from(self.start_point)
        self.loader = UYVYStreamLoader(feed=feed)
        self.loader.link_from(self.rpt)
        self.end_point.link_from(self.loader)
        self.end_point.gate_skip = self.loader.complete
        self.end_point.gate_skip_not = [1]
        self.end_point.gate_block = [0]
        self.end_point.gate_block_not = [0]
        self.forward[0].link_from(self.end_point)
        self.forward[0].input = self.loader.minibatch_data
        for i in range(1, len(self.forward)):
            self.forward[i].link_from(self.forward[i - 1])
        self.plt_result = tv_channel_plotter.ResultPlotter()
        self.plt_result.link_from(self.forward[-1])
        self.plt_result.input = self.forward[-1].max_idx
        self.plt_result.image = self.loader.minibatch_data
        self.rpt.link_from(self.plt_result)


class UYVYStreamLoader(units.Unit):
    """Provides samples from UYVY packed raw video stream.

    Attributes:
        feed: pipe with video stream.
        frame_width: video frame width.
        frame_height: video frame height.
        x: output rectangle left.
        y: output rectangle top.
        width: output rectangle width.
        height: output rectangle height.
        scale: factor to scale frame.
        gray: if grayscale.
    """
    def __init__(self, feed=None, frame_width=1920, frame_height=1080,
                 x=66, y=64, width=464, height=128, scale=0.5, gray=True):
        super(UYVYStreamLoader, self).__init__()
        self.feed = feed
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.scale = scale
        self.gray = gray
        self.minibatch_data = formats.Vector()
        self.minibatch_size = [1]
        self.complete = [0]
        self.cc = None

    def initialize(self):
        self.cy = numpy.zeros([self.height, self.width], dtype=numpy.uint8)
        self.cu = numpy.zeros([self.height, self.width >> 1],
            dtype=numpy.uint8)
        self.cv = numpy.zeros([self.height, self.width >> 1],
            dtype=numpy.uint8)

        self.aw = int(numpy.round(self.width * self.scale))
        self.ah = int(numpy.round(self.height * self.scale))
        if self.gray:
            self.subframe = numpy.zeros([self.ah, self.aw], dtype=numpy.uint8)
        else:
            self.subframe = numpy.zeros([self.ah << 1, self.aw],
                dtype=numpy.uint8)
        self.minibatch_data.v = numpy.zeros([1, self.subframe.shape[0],
            self.subframe.shape[1]], dtype=config.dtypes[config.dtype])

    def run(self):
        if self.complete[0]:
            return
        try:
            n = self.frame_width * self.frame_height * 2
            s = self.feed.read(n)
            frame_img = numpy.frombuffer(s, dtype=numpy.uint8, count=n).\
                reshape(self.frame_height, self.frame_width // 2, 4)
            img = frame_img[self.y:self.y + self.height,
                self.x // 2:(self.x + self.width) // 2]
        except ValueError:
            self.complete[0] = 1
            return
        y = self.cy
        u = self.cu
        v = self.cv

        for row in range(0, img.shape[0]):
            for col in range(0, img.shape[1]):
                pix = img[row, col]
                u[row, col] = pix[0]
                v[row, col] = pix[2]
                y[row, col << 1] = pix[1]
                y[row, (col << 1) + 1] = pix[3]

        if self.scale != 1.0:
            ay = scipy.ndimage.zoom(y, self.scale, order=1)
            if not self.gray:
                au = scipy.ndimage.zoom(u, self.scale, order=1)
                av = scipy.ndimage.zoom(v, self.scale, order=1)
        else:
            ay = y
            au = u
            av = v

        a = self.subframe

        a[:self.ah, :] = ay[:]
        if not self.gray:
            a[self.ah:, :self.aw >> 1] = au
            a[self.ah:, self.aw >> 1:] = av

        sample = self.minibatch_data.v[0]
        sample[:] = a[:]
        formats.normalize(sample)
        self.minibatch_data.update()


def main():
    if __debug__:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    """
    fin = open("mnist.1.86.2layer100neurons.pickle", "rb")
    w = pickle.load(fin)
    fin.close()

    fout = open("w100.txt", "w")
    weights = w.forward[0].weights.v
    for row in weights:
        fout.write(" ".join("%.6f" % (x) for x in row))
        fout.write("\n")
    fout.close()
    fout = open("b100.txt", "w")
    bias = w.forward[0].bias.v
    fout.write(" ".join("%.6f" % (x) for x in bias))
    fout.write("\n")
    fout.close()

    fout = open("w10.txt", "w")
    weights = w.forward[1].weights.v
    for row in weights:
        fout.write(" ".join("%.6f" % (x) for x in row))
        fout.write("\n")
    fout.close()
    fout = open("b10.txt", "w")
    bias = w.forward[1].bias.v
    fout.write(" ".join("%.6f" % (x) for x in bias))
    fout.write("\n")
    fout.close()

    logging.info("Done")
    sys.exit(0)
    """
    global this_dir
    rnd.default.seed(numpy.fromfile("%s/seed" % (this_dir),
                                    numpy.int32, 1024))
    # rnd.default.seed(numpy.fromfile("/dev/urandom", numpy.int32, 1024))
    try:
        #device = None
        cl = opencl.DeviceList()
        device = cl.get_device()
        w = Workflow(layers=[15, 13], device=device)
        w.initialize(threshold=1.0, threshold_low=1.0,
              global_alpha=0.001, global_lambda=0.0,
              minibatch_maxsize=27, device=device)
        try:
            fin = open("%s/channels_Wb.pickle" % (config.snapshot_dir), "rb")
            W, b = pickle.load(fin)
            fin.close()
            for i in range(0, len(W)):
                w.forward[i].weights.v[:] = W[i][:]
                w.forward[i].bias.v[:] = b[i][:]
                w.forward[i].weights.update()
                w.forward[i].bias.update()
        except IOError:
            pass
    except KeyboardInterrupt:
        return
    try:
        w.run()
    except KeyboardInterrupt:
        w.gd[-1].gate_block = [1]
    """
    logging.info("Will snapshot in 15 seconds...")
    time.sleep(5)
    logging.info("Will snapshot in 10 seconds...")
    time.sleep(5)
    logging.info("Will snapshot in 5 seconds...")
    time.sleep(5)
    fnme = "%s/channels.pickle" % (this_dir)
    logging.info("Snapshotting to %s" % (fnme))
    fout = open(fnme, "wb")
    pickle.dump(w, fout)
    fout.close()
    """

    try:
        plotters.Graphics().wait_finish()
    except:
        pass
    logging.info("End of job")


if __name__ == "__main__":
    main()
    sys.exit(0)
