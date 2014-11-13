#!/usr/bin/python3 -O
"""
Created on Mart 21, 2014

Configuration file for Mnist. Model – fully-connected
Neural Network with MSE loss function with target encoded as ideal image
(784 points).

Copyright (c) 2013 Samsung Electronics Co., Ltd.
"""


import os

from veles.config import root


mnist_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "samples/MNIST")
test_image_dir = os.path.join(mnist_dir, "t10k-images.idx3-ubyte")
test_label_dir = os.path.join(mnist_dir, "t10k-labels.idx1-ubyte")
train_image_dir = os.path.join(mnist_dir, "train-images.idx3-ubyte")
train_label_dir = os.path.join(mnist_dir, "train-labels.idx1-ubyte")


root.mnist784.update({
    "decision": {"fail_iterations": 100, "max_epochs": 100000},
    "snapshotter": {"prefix": "mnist_784"},
    "loader": {"minibatch_size": 100, "on_device": True},
    "weights_plotter": {"limit": 16},
    "learning_rate": 0.00001,
    "weights_decay": 0.00005,
    "layers": [784, 784],
    "data_paths": {"test_images": test_image_dir,
                   "test_label": test_label_dir,
                   "train_images": train_image_dir,
                   "train_label": train_label_dir,
                   "arial": os.path.join(root.common.test_dataset_root,
                                         "arial.ttf")}})
