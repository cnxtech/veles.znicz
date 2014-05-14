#include "defines.cl"
#include "highlight.cl"

/// @brief Kohonen forward propagation.
/// @param h input.
/// @param weights weights.
/// @param y output.
/// @details y = W * h.
///          Must be defined externally:
///          BLOCK_SIZE - size of the block for matrix multiplication,
///          BATCH - minibatch size,
///          SAMPLE_LENGTH - input size,
///          NEURONS_NUMBER - output size.
__kernel __attribute__((reqd_work_group_size(BLOCK_SIZE, BLOCK_SIZE, 1)))
void feed_layer(__global c_dtype    /* IN */    *input,
                __global c_dtype    /* IN */    *weights,
                __global c_dtype   /* OUT */    *output) {
  #define A_WIDTH BATCH
  #define B_WIDTH NEURONS_NUMBER
  #define AB_COMMON SAMPLE_LENGTH

  #define A input
  #define B weights

  #ifdef WEIGHTS_TRANSPOSED
  #define B_COL
  #endif

  #include "matrix_multiplication.cl"

  #undef A_WIDTH
  #undef B_WIDTH
  #undef AB_COMMON

  #undef A
  #undef B

  if (valid) {
    output[idx] = sum[0];
  }
}

#ifdef TRAIN
/// @brief Computes distances between input and neuron weights.
/// @param h input.
/// @param weights weights.
/// @param y distance(h, weights).
/// @details Must be defined externally:
///          BATCH - minibatch size,
///          SAMPLE_LENGTH - the length of each sample,
///          NEURONS_NUMBER - the number of neurons.
__kernel __attribute__((reqd_work_group_size(BLOCK_SIZE, BLOCK_SIZE, 1)))
void compute_distance(__global const c_dtype    /* IN */    *input,
                      __global const c_dtype    /* IN */    *weights,
                      __global dtype           /* OUT */    *output) {
  #define A_WIDTH BATCH
  #define B_WIDTH NEURONS_NUMBER
  #define AB_COMMON SAMPLE_LENGTH

  #define A input
  #define B weights

  #ifdef WEIGHTS_TRANSPOSED
  #define B_COL
  #endif

  #define MULTIPLY c_dist2

  #include "matrix_multiplication.cl"

  #undef A_WIDTH
  #undef B_WIDTH
  #undef AB_COMMON

  #undef A
  #undef B

  if (valid) {
    output[idx] = sum[0];
  }
}


/// @brief Kohonen train pass.
/// @param dists Values to find minimum of.
/// @param argmin Indices of min elements. May be not initialized.
/// @details Must be defined externally:
///          BATCH - the number of samples, the size of argmin,
///          CHUNK_SIZE - the number of distances processed by each thread,
///          NEURONS_NUMBER - the number of neurons.
#if NEURONS_NUMBER % CHUNK_SIZE > 0
#define WORK_GROUP_SIZE (NEURONS_NUMBER / CHUNK_SIZE + 1)
#else
#define WORK_GROUP_SIZE (NEURONS_NUMBER / CHUNK_SIZE)
#endif
__kernel __attribute__((reqd_work_group_size(WORK_GROUP_SIZE, 1, 1)))
void compute_argmin(__global const dtype /* IN */   *dists,
                    __global int         /* OUT */  *argmin) {

  int tx = get_local_id(0); // from 0 to WORK_GROUP_SIZE - 1

  __local dtype mins[BATCH * WORK_GROUP_SIZE];
  __local dtype argmins[BATCH * WORK_GROUP_SIZE];

  for (int sample = 0; sample < BATCH; sample++) {
    dtype min_value = MAXFLOAT;
    int min_index = -1;
    int offset = sample * NEURONS_NUMBER;
    for (int i = offset + tx * CHUNK_SIZE;
         i < offset + MIN((tx + 1) * CHUNK_SIZE, NEURONS_NUMBER);
         i++) {
      dtype value = dists[i];
      if (value < min_value) {
        min_value = value;
        min_index = i - offset;
      }
    }
    mins[sample * WORK_GROUP_SIZE + tx] = min_value;
    argmins[sample * WORK_GROUP_SIZE + tx] = min_index;
  }
  barrier(CLK_LOCAL_MEM_FENCE);

  for (int sample = tx; sample < BATCH; sample += BATCH / WORK_GROUP_SIZE) {
    int offset = sample * WORK_GROUP_SIZE;
    dtype min_value = MAXFLOAT;
    int min_index = -1;
    for (int i = offset; i < offset + WORK_GROUP_SIZE; i++) {
      dtype value = mins[i];
      if (value < min_value) {
        min_value = value;
        min_index = argmins[i];
      }
    }
    argmin[sample] = min_index;
  }
}
#undef WORK_GROUP_SIZE


/// @brief Computes gravity function from argmin neuron to all others.
/// @param argmin Indexes of neurons with min distances to inputs.
/// @param coords Neuron coordinates in Euclidian space.
/// @param gravity Output gravity.
/// @param sigma Effective radius.
/// @details Must be defined externally:
///          NEURONS_NUMBER - output size,
///          coord_type - type for coordinates of neuron in space (float2).
__kernel
void compute_gravity(__global const int           /* IN */    *argmin,
                     __global const coord_type    /* IN */    *coords,
                     const dtype                  /* IN */    sigma,
                     __global dtype              /* OUT */    *gravity) {
  int src = get_global_id(0);
  int dst = get_global_id(1);
  dtype d = distance(coords[argmin[src]], coords[dst]);
  gravity[src * NEURONS_NUMBER + dst] = exp((d * d) / (-2 * sigma * sigma));
}

/// @brief Updates weights according to Kohonen's learning algorithm.
/// @param input The input samples.
/// @param weights The Weights.
/// @param gravity Gravity function for each neuron relative to the winner.
/// @param time_reciprocal 1 / t
/// @details Must be defined externally:
///          BATCH - the number of samples, the size of argmin,
///          CHUNK_SIZE - the number of weights processed by each thread,
///          NEURONS_NUMBER - the number of neurons.
__kernel
void apply_gradient(__global const c_dtype /* IN */      *input,
                    __global const dtype   /* IN */      *gravity,
                    const dtype            /* IN */      time_reciprocal,
                    __global c_dtype       /* IN, OUT */ *weights) {
  int tx = get_global_id(0);

  c_dtype orig_weights[CHUNK_SIZE * SAMPLE_LENGTH];
  for (int nindex = tx * CHUNK_SIZE;
       nindex < MIN((tx + 1) * CHUNK_SIZE, NEURONS_NUMBER);
       nindex++) {
#ifndef WEIGHTS_TRANSPOSED
    int weights_offset = nindex * SAMPLE_LENGTH;
    for (int windex = weights_offset;
         windex < weights_offset + SAMPLE_LENGTH;
         windex++) {
      orig_weights[(nindex - tx * CHUNK_SIZE) * SAMPLE_LENGTH +
                   windex - weights_offset] = weights[windex];
    }
#else
    for (int windex = nindex;
         windex < NEURONS_NUMBER * SAMPLE_LENGTH;
         windex += NEURONS_NUMBER) {
      orig_weights[windex + nindex - tx * CHUNK_SIZE] = weights[windex];
    }
#endif
  }

  for (int sample = 0; sample < BATCH; sample++) {
    for (int nindex = tx * CHUNK_SIZE;
         nindex < MIN((tx + 1) * CHUNK_SIZE, NEURONS_NUMBER);
         nindex++) {
#ifndef WEIGHTS_TRANSPOSED
      int weights_offset = nindex * SAMPLE_LENGTH;
      for (int windex = 0; windex <  SAMPLE_LENGTH; windex++) {
        weights[windex + weights_offset] +=
            gravity[sample * NEURONS_NUMBER + nindex] * time_reciprocal *
            (input[sample * SAMPLE_LENGTH + windex] -
             orig_weights[(nindex - tx * CHUNK_SIZE) * SAMPLE_LENGTH + windex]);
      }
#else
      for (int windex = nindex;
           windex < NEURONS_NUMBER * SAMPLE_LENGTH;
           windex += NEURONS_NUMBER) {
        weights[windex] +=
            gravity[sample * NEURONS_NUMBER + nindex] * time_reciprocal *
            (input[sample * SAMPLE_LENGTH + windex / NEURONS_NUMBER] -
             orig_weights[windex + nindex - tx * CHUNK_SIZE]);
      }
#endif
    }
  }
}

#endif  // TRAIN