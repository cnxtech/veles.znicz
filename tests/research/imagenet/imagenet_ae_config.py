"""
Created on Jule 18, 2014

Copyright (c) 2013 Samsung Electronics Co., Ltd.
"""

from veles.config import root


LR = 0.00001
WD = 0.004
GM = 0.9
L1_VS_L2 = 0.0

LRAA = 0.01
LRBAA = 2 * LRAA
WDAA = 0.004
WDBAA = 0
GMAA = 0.9
GMBAA = GM

FILLING = "gaussian"
STDDEV_CONV = 0.01
STDDEV_AA = 0.001

root.update = {
    "decision": {"fail_iterations": 25,
                 "use_dynamic_alpha": False,
                 "do_export_weights": True},
    "loader": {"year": "temp",
               "series": "img",
               "minibatch_size": 30},
    "imagenet": {"from_snapshot_add_layer": True,
                 "fine_tuning_noise": 1.0e-6,
                 "layers":
                 [{"type": "ae_begin"},  # 256
                  {"type": "conv", "n_kernels": 64,
                   "kx": 9, "ky": 9, "sliding": (3, 3),
                   "learning_rate": LR,
                   "weights_decay": WD,
                   "gradient_moment": GM,
                   "weights_filling": FILLING,
                   "weights_stddev": STDDEV_CONV,
                   "l1_vs_l2": L1_VS_L2},
                  #{"type": "stochastic_abs_pooling",
                  # "kx": 3, "ky": 3, "sliding": (2, 2)},
                  {"type": "ae_end"},

                  {"type": "activation_mul"},
                  {"type": "ae_begin"},  # 128
                  {"type": "conv", "n_kernels": 64,
                   "kx": 6, "ky": 6, "sliding": (2, 2),
                   "learning_rate": LR,
                   "weights_decay": WD,
                   "gradient_moment": GM,
                   "weights_filling": FILLING,
                   "weights_stddev": STDDEV_CONV,
                   "l1_vs_l2": L1_VS_L2},
                  #{"type": "stochastic_abs_pooling",
                  # "kx": 3, "ky": 3, "sliding": (2, 2)},
                  {"type": "ae_end"},

                  {"type": "activation_mul"},
                  {"type": "ae_begin"},  # 64
                  {"type": "conv", "n_kernels": 128,
                   "kx": 6, "ky": 6, "sliding": (2, 2),
                   "learning_rate": LR,
                   "weights_decay": WD,
                   "gradient_moment": GM,
                   "weights_filling": FILLING,
                   "weights_stddev": STDDEV_CONV,
                   "l1_vs_l2": L1_VS_L2},
                  #{"type": "stochastic_abs_pooling",
                  # "kx": 3, "ky": 3, "sliding": (2, 2)},
                  {"type": "ae_end"},

                  {"type": "activation_mul"},
                  {"type": "ae_begin"},  # 64
                  {"type": "conv", "n_kernels": 192,
                   "kx": 4, "ky": 4, "sliding": (2, 2),
                   "learning_rate": LR,
                   "weights_decay": WD,
                   "gradient_moment": GM,
                   "weights_filling": FILLING,
                   "weights_stddev": STDDEV_CONV,
                   "l1_vs_l2": L1_VS_L2},
                  #{"type": "stochastic_abs_pooling",
                  # "kx": 3, "ky": 3, "sliding": (2, 2)},
                  {"type": "ae_end"},

                  {"type": "activation_mul"},
                  {"type": "all2all_tanh", "output_shape": 100,
                   "learning_rate": LRAA, "learning_rate_bias": LRBAA,
                   "weights_decay": WDAA, "weights_decay_bias": WDBAA,
                   "gradient_moment": GMAA, "gradient_moment_bias": GMBAA,
                   "weights_filling": "gaussian", "bias_filling": "gaussian",
                   "weights_stddev": STDDEV_AA, "bias_stddev": STDDEV_AA,
                   "l1_vs_l2": L1_VS_L2},

                  {"type": "softmax", "output_shape": 5,
                   "learning_rate": LRAA, "learning_rate_bias": LRBAA,
                   "weights_decay": WDAA, "weights_decay_bias": WDBAA,
                   "gradient_moment": GMAA, "gradient_moment_bias": GMBAA,
                   "weights_filling": "gaussian", "bias_filling": "gaussian",
                   "l1_vs_l2": L1_VS_L2}]}}
