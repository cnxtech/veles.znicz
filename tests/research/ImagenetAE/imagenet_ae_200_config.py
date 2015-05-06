# -*- coding: utf-8 -*-
"""
.. invisible:
     _   _ _____ _     _____ _____
    | | | |  ___| |   |  ___/  ___|
    | | | | |__ | |   | |__ \ `--.
    | | | |  __|| |   |  __| `--. \
    \ \_/ / |___| |___| |___/\__/ /
     \___/\____/\_____|____/\____/

Created on Jule 18, 2014

Configuration file for imagenet_ae with stochastic pooling.
Number of classes - 200. (DET)

███████████████████████████████████████████████████████████████████████████████

Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.

███████████████████████████████████████████████████████████████████████████████
"""


import os

from veles.config import root


LR = 0.000002
WD = 0.0005
ORTHO = 0.001
GM = 0.9
L1_VS_L2 = 0.0

LRFT = 0.01
LRFTB = LRFT * 2

LRAA = 0.01
LRBAA = LRAA * 2
WDAA = 0.0005
ORTHOAA = 0.001
WDBAA = 0
GMAA = 0.9
GMBAA = GM

FILLING = "gaussian"
STDDEV_CONV = 0.01
STDDEV_AA = 0.005

root.common.precision_type = "float"
root.imagenet_ae.model = "imagenet"
root.imagenet_ae.update({
    "decision": {"fail_iterations": 50,
                 "max_epochs": 50},
    "loader_name": "imagenet_ae_loader",
    "loader": {"year": "2014",
               "series": "DET",
               "minibatch_size": 120,
               "path": "/export/home/imagenet",
               "sx": 216,
               "sy": 216},
    "image_saver": {"out_dirs":
                    [os.path.join(root.common.cache_dir,
                                  "tmp_imagenet/test"),
                     os.path.join(root.common.cache_dir,
                                  "tmp_imagenet/validation"),
                     os.path.join(root.common.cache_dir,
                                  "tmp_imagenet/train")]},
    "snapshotter": {"prefix": "imagenet_ae",
                    "directory":
                    os.path.join(root.common.test_dataset_root,
                                 "imagenet/snapshots/DET/new")},
    "from_snapshot_add_layer": True,
    "fine_tuning_noise": 1.0e-6,
    "layers":
    [{"type": "ae_begin"},  # 216
     {"type": "conv", "n_kernels": 108,
      "kx": 9, "ky": 9, "sliding": (1, 1),
      "learning_rate": LR,
      "learning_rate_ft": LRFT,
      "weights_decay": WD,
      "factor_ortho": ORTHO,
      "gradient_moment": GM,
      "weights_filling": FILLING,
      "weights_stddev": STDDEV_CONV,
      "l1_vs_l2": L1_VS_L2},
     {"type": "stochastic_abs_pooling",
      "kx": 3, "ky": 3, "sliding": (3, 3)},
     {"type": "ae_end"},
     {"type": "activation_mul"},
     {"type": "ae_begin"},  # 72
     {"type": "conv", "n_kernels": 192,
      "kx": 6, "ky": 6, "sliding": (1, 1),
      "learning_rate": LR,
      "learning_rate_ft": LRFT,
      "weights_decay": WD,
      "factor_ortho": ORTHO,
      "gradient_moment": GM,
      "weights_filling": FILLING,
      "weights_stddev": STDDEV_CONV,
      "l1_vs_l2": L1_VS_L2},
     {"type": "stochastic_abs_pooling",
      "kx": 2, "ky": 2, "sliding": (2, 2)},
     {"type": "ae_end"},
     {"type": "activation_mul"},
     {"type": "ae_begin"},  # 36
     {"type": "conv", "n_kernels": 224,
      "kx": 6, "ky": 6, "sliding": (1, 1),
      "learning_rate": LR,
      "learning_rate_ft": LRFT,
      "weights_decay": WD,
      "factor_ortho": ORTHO,
      "gradient_moment": GM,
      "weights_filling": FILLING,
      "weights_stddev": STDDEV_CONV,
      "l1_vs_l2": L1_VS_L2},
     {"type": "stochastic_abs_pooling",
      "kx": 2, "ky": 2, "sliding": (2, 2)},
     {"type": "ae_end"},
     {"type": "activation_mul"},
     {"type": "ae_begin"},  # 18
     {"type": "conv", "n_kernels": 256,
      "kx": 6, "ky": 6, "sliding": (1, 1),
      "learning_rate": LR,
      "learning_rate_ft": LRFT,
      "weights_decay": WD,
      "factor_ortho": ORTHO,
      "gradient_moment": GM,
      "weights_filling": FILLING,
      "weights_stddev": STDDEV_CONV,
      "l1_vs_l2": L1_VS_L2},
     {"type": "stochastic_abs_pooling",
      "kx": 2, "ky": 2, "sliding": (2, 2)},
     {"type": "ae_end"},
     {"type": "activation_mul"},
     {"type": "all2all_tanh", "output_sample_shape": 2048,
      "learning_rate": LRAA, "learning_rate_bias": LRBAA,
      "learning_rate_ft": LRFT, "learning_rate_ft_bias": LRFTB,
      "weights_decay": WDAA, "weights_decay_bias": WDBAA,
      "factor_ortho": ORTHOAA,
      "gradient_moment": GMAA, "gradient_moment_bias": GMBAA,
      "weights_filling": "gaussian", "bias_filling": "gaussian",
      "weights_stddev": STDDEV_AA, "bias_stddev": STDDEV_AA,
      "l1_vs_l2": L1_VS_L2},
     {"type": "dropout", "dropout_ratio": 0.5},
     {"type": "all2all_tanh", "output_sample_shape": 2048,
      "learning_rate": LRAA, "learning_rate_bias": LRBAA,
      "learning_rate_ft": LRFT, "learning_rate_ft_bias": LRFTB,
      "weights_decay": WDAA, "weights_decay_bias": WDBAA,
      "factor_ortho": ORTHOAA,
      "gradient_moment": GMAA, "gradient_moment_bias": GMBAA,
      "weights_filling": "gaussian", "bias_filling": "gaussian",
      "weights_stddev": STDDEV_AA, "bias_stddev": STDDEV_AA,
      "l1_vs_l2": L1_VS_L2},
     {"type": "dropout", "dropout_ratio": 0.5},
     {"type": "softmax", "output_sample_shape": 201,
      "learning_rate": LRAA, "learning_rate_bias": LRBAA,
      "learning_rate_ft": LRFT, "learning_rate_ft_bias": LRFTB,
      "weights_decay": WDAA, "weights_decay_bias": WDBAA,
      "gradient_moment": GMAA, "gradient_moment_bias": GMBAA,
      "weights_filling": "gaussian", "bias_filling": "gaussian",
      "bias_stddev": 0.01, "weights_stddev": 0.01,
      "l1_vs_l2": L1_VS_L2}]})