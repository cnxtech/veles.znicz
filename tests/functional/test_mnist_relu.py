#!/usr/bin/python3 -O
"""
Created on April 2, 2014

Copyright (c) 2013 Samsung Electronics Co., Ltd.
"""


from veles.config import root
from veles.snapshotter import Snapshotter
from veles.tests import timeout, multi_device
from veles.znicz.tests.functional import StandardTest
import veles.znicz.tests.research.MNIST.mnist as mnist_relu
import veles.dummy as dummy_workflow


class TestMnistRelu(StandardTest):
    @classmethod
    def setUpClass(cls):
        root.mnistr.update({
            "loss_function": "softmax",
            "loader_name": "mnist_loader",
            "learning_rate_adjust": {"do": False},
            "all2all": {"weights_stddev": 0.05},
            "decision": {"fail_iterations": (0)},
            "snapshotter": {"prefix": "mnist_relu_test"},
            "loader": {"minibatch_size": 60, "normalization_type": "linear"},
            "layers": [{"type": "all2all_relu",
                        "->": {"output_sample_shape": 100,
                               "weights_filling": "uniform",
                               "weights_stddev": 0.05,
                               "bias_filling": "uniform", "bias_stddev": 0.05},
                        "<-": {"learning_rate": 0.03, "weights_decay": 0.0,
                               "learning_rate_bias": 0.03,
                               "weights_decay_bias": 0.0,
                               "gradient_moment": 0.0,
                               "gradient_moment_bias": 0.0,
                               "factor_ortho": 0.001}},
                       {"type": "softmax",
                        "->": {"output_sample_shape": 10,
                               "weights_filling": "uniform",
                               "weights_stddev": 0.05,
                               "bias_filling": "uniform", "bias_stddev": 0.05},
                        "<-": {"learning_rate": 0.03,
                               "learning_rate_bias": 0.03,
                               "weights_decay": 0.0,
                               "weights_decay_bias": 0.0,
                               "gradient_moment": 0.0,
                               "gradient_moment_bias": 0.0}}]})

    @timeout(300)
    @multi_device()
    def test_mnist_relu(self):
        self.info("Will test mnist workflow with relu config")

        self.w = mnist_relu.MnistWorkflow(
            dummy_workflow.DummyLauncher(),
            decision_config=root.mnistr.decision,
            snapshotter_config=root.mnistr.snapshotter,
            loader_name=root.mnistr.loader_name,
            loader_config=root.mnistr.loader,
            layers=root.mnistr.layers,
            loss_function=root.mnistr.loss_function)
        self.w.decision.max_epochs = 2
        self.w.snapshotter.time_interval = 0
        self.w.snapshotter.interval = 2 + 1
        self.assertEqual(self.w.evaluator.labels,
                         self.w.loader.minibatch_labels)
        self.w.initialize(device=self.device, snapshot=False)
        self.assertEqual(self.w.evaluator.labels,
                         self.w.loader.minibatch_labels)
        self.w.run()
        file_name = self.w.snapshotter.file_name

        err = self.w.decision.epoch_n_err[1]
        self.assertEqual(err, 840)
        self.assertEqual(2, self.w.loader.epoch_number)

        self.info("Will load workflow from %s", file_name)
        self.wf = Snapshotter.import_(file_name)
        self.assertTrue(self.wf.decision.epoch_ended)
        self.wf.decision.max_epochs = 5
        self.wf.decision.complete <<= False
        self.assertEqual(self.wf.evaluator.labels,
                         self.wf.loader.minibatch_labels)
        self.wf.initialize(device=self.device, snapshot=True)
        self.assertEqual(self.wf.evaluator.labels,
                         self.wf.loader.minibatch_labels)
        self.wf.run()

        err = self.wf.decision.epoch_n_err[1]
        self.assertEqual(err, 566)
        self.assertEqual(5, self.wf.loader.epoch_number)
        self.info("All Ok")

if __name__ == "__main__":
    StandardTest.main()
