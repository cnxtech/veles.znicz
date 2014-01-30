"""
Created on Nov 8, 2013

Will test correctness of OpenCL matrix multiplication.

@author: Kazantsev Alexey <a.kazantsev@samsung.com>
"""
import unittest
import opencl
import numpy
import config
import znicz_config
import formats
import rnd
import pyopencl
import units
import os


class TestMatrixMultiplication(unittest.TestCase):
    def _do_cpu_tst(self):
        """Pure single core CPU test
        """
        dtype = (numpy.complex128 if self.a.v.dtype in (
                    numpy.complex64, numpy.complex128) else numpy.float64)
        a = numpy.empty(self.a.v.shape, dtype=dtype)
        a[:] = self.a.v[:]
        bt = self.b.v.transpose()
        b = numpy.empty(bt.shape, dtype=dtype)
        b[:] = bt[:]
        bias = numpy.empty(self.bias.v.shape, dtype=dtype)
        bias[:] = self.bias.v[:]
        c = numpy.empty(self.c.v[0].shape, dtype=dtype)
        numpy.dot(a, b, c)
        c[:] += bias
        c *= 0.6666
        numpy.tanh(c, c)
        c *= 1.7159
        return c

    def _prepare_tsts(self, BLOCK_SIZE, dtype=config.dtypes[config.dtype],
                      AB_WIDTH=1371, B_HEIGHT=11735, A_HEIGHT=171):
        self.AB_WIDTH = AB_WIDTH
        self.B_HEIGHT = B_HEIGHT
        self.A_HEIGHT = A_HEIGHT

        self.a = formats.Vector()
        self.a.v = numpy.zeros([self.A_HEIGHT * self.AB_WIDTH], dtype=dtype)
        rnd.default.fill(self.a.v, -0.1, 0.1)
        self.a.v = self.a.v.reshape([self.A_HEIGHT, self.AB_WIDTH])

        self.b = formats.Vector()
        self.b.v = numpy.zeros([self.B_HEIGHT * self.AB_WIDTH], dtype=dtype)
        rnd.default.fill(self.b.v, -0.1, 0.1)
        self.b.v = self.b.v.reshape([self.B_HEIGHT, self.AB_WIDTH])

        self.bias = formats.Vector()
        self.bias.v = numpy.zeros([self.B_HEIGHT], dtype=dtype)
        rnd.default.fill(self.bias.v, -0.1, 0.1)

        self.c = formats.Vector()
        self.c.v = numpy.zeros([2, self.A_HEIGHT, self.B_HEIGHT], dtype=dtype)

    def _cleanup_after_tsts(self):
        del(self.c)
        del(self.bias)
        del(self.b)
        del(self.a)
        del(self.A_HEIGHT)
        del(self.B_HEIGHT)
        del(self.AB_WIDTH)

    def _do_tst(self, device, BLOCK_SIZE):
        """Do test for specific context
        """
        defines = ("%s\n"
        "#define ACTIVATION_TANH\n"
        "#define BLOCK_SIZE %d\n"
        "#define H %d\n"
        "#define Y %d\n"
        "#define BATCH %d\n\n" % (config.cl_defines[config.dtype], BLOCK_SIZE,
                                  self.AB_WIDTH, self.B_HEIGHT, self.A_HEIGHT))
        s = defines
        s += units.OpenCLUnit.read_ocl_file("defines.cl")
        s_mx_mul = units.OpenCLUnit.read_ocl_file("matrix_multiplication.cl")
        s += units.OpenCLUnit.read_ocl_file("forward.cl")
        s = s.replace("MX_MUL", s_mx_mul)
        fout = open(os.path.join(config.cache_dir, "test.cl"), "w")
        fout.write(s)
        fout.close()

        self.a.initialize(device)
        self.b.initialize(device)
        self.c[:] = 0
        self.c.initialize(device)
        self.bias.initialize(device)

        prg = pyopencl.Program(device.context_, s).build()

        krn = pyopencl.Kernel(prg, "feed_layer")
        krn.set_arg(0, self.a.v_)
        krn.set_arg(1, self.b.v_)
        krn.set_arg(2, self.c.v_)
        krn.set_arg(3, self.bias.v_)

        global_size = [formats.roundup(self.B_HEIGHT, BLOCK_SIZE),
                       formats.roundup(self.A_HEIGHT, BLOCK_SIZE)]
        local_size = [BLOCK_SIZE, BLOCK_SIZE]

        event = pyopencl.enqueue_nd_range_kernel(device.queue_, krn,
                                                 global_size, local_size)
        event.wait()

        self.c.map_read()

    def test_matrix_multiplication(self):
        self.rnd = rnd.Rand()
        self.rnd.seed(numpy.fromfile("/dev/urandom", dtype=numpy.int32,
                                     count=1024))
        device = opencl.Device()
        self.assertNotEqual(device, None, "Could not get OpenCL device.")
        block_size = device.info.BLOCK_SIZE[config.dtype]
        N = 1000
        print("Will test %d matrix multiplications "
              "with BLOCK_SIZE = %d" % (N, block_size))
        for i in range(0, N, 47):
            AB_WIDTH = self.rnd.randint(1, ((i // 10) + 1) * 100)
            B_HEIGHT = self.rnd.randint(1, ((i // 10) + 1) * 10)
            A_HEIGHT = self.rnd.randint(1, ((i // 10) + 1) * 10)
            print("%d: [%d, %d] * [%d, %d] = [%d, %d]" % (i,
                AB_WIDTH, A_HEIGHT, B_HEIGHT, AB_WIDTH,
                A_HEIGHT, B_HEIGHT))
            self._prepare_tsts(block_size, AB_WIDTH=AB_WIDTH,
                               B_HEIGHT=B_HEIGHT, A_HEIGHT=A_HEIGHT)
            c = self._do_cpu_tst()
            self._do_tst(device, block_size)
            max_diff = numpy.fabs(c.ravel() - self.c.v[0].ravel()).max()
            self.assertLess(max_diff, 0.0001,
                            "Result differs by %.6f" % (max_diff))
            num_nz = numpy.count_nonzero(self.c.v[1].ravel())
            self.assertEqual(num_nz, 0,
                "Written some values outside of the target array bounds")
            self._cleanup_after_tsts()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()