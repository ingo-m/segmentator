#!/usr/bin/env python
"""Common functions used in filters."""

# Part of the Segmentator library
# Copyright (C) 2018  Omer Faruk Gulban and Marian Schneider
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division
import numpy as np
from scipy.ndimage.filters import gaussian_filter


def self_outer_product(vector_field):
    """Vectorized computation of outer product.

    Parameters
    ----------
    vector_field: np.ndarray, shape(..., 3)

    Returns
    -------
    outer: np.ndarray, shape(..., 3, 3)
    """
    dims = vector_field.shape
    outer = np.repeat(vector_field, dims[-1], axis=-1)
    outer *= outer[..., [0, 3, 6, 1, 4, 7, 2, 5, 8]]
    outer = outer.reshape(dims[:-1] + (dims[-1], dims[-1]))
    return outer


def dot_product_matrix_vector(matrix_field, vector_field):
    """Vectorized computation of dot product."""
    dims = vector_field.shape
    dotp = np.repeat(vector_field, dims[-1], axis=-1)
    dotp = dotp.reshape(dims[:-1] + (dims[-1], dims[-1]))
    idx_dims = tuple(range(dotp.ndim))
    dotp = dotp.transpose(idx_dims[:-2] + (idx_dims[-1], idx_dims[-2]))
    np.multiply(matrix_field, dotp, out=dotp)
    dotp = np.sum(dotp, axis=-1)
    return dotp


def divergence(vector_field):
    """Vectorized computation of divergence, also called Laplacian."""
    dims = vector_field.shape
    result = np.zeros(dims[:-1])
    for i in range(dims[-1]):
        result += np.gradient(vector_field[..., i], axis=i)
    return result


def compute_diffusion_weights(eigvals, mode, LAMBDA=0.001, ALPHA=0.001, M=4):
    """Vectorized computation diffusion weights.

    Reference
    ---------
    - Mirebeau, J.-M., Fehrenbach, J., Risser, L., & Tobji, S. (2015).
    Anisotropic Diffusion in ITK, 1-9.
    """
    idx_pos_e2 = eigvals[:, 1] > 0  # positive indices of second eigen value
    c = (1. - ALPHA)  # related to matrix condition

    if mode in ['EED', 'cEED', 'iEED']:

        if mode == 'EED':  # edge enhancing diffusion
            mu = np.ones(eigvals.shape)
            term1 = LAMBDA
            term2 = eigvals[idx_pos_e2, 1:] - eigvals[idx_pos_e2, 0, None]
            mu[idx_pos_e2, 1:] = 1. - c * np.exp(-(term1/term2)**M)
            # weights for the non-positive eigen values
            mu[~idx_pos_e2, 2] = ALPHA  # surely surfels

        elif mode == 'cEED':  # FIXME: Not working at all, for now...
            term1 = LAMBDA
            term2 = eigvals
            mu = 1. - c * np.exp(-(term1/term2)**M)

    elif mode in ['CED', 'cCED']:

        if mode == 'CED':  # coherence enhancing diffusion
            mu = np.ones(eigvals.shape) * ALPHA
            term1 = LAMBDA
            term2 = eigvals[:, 2, None] - eigvals[:, :-1]
            mu[:, :-1] = ALPHA + c * np.exp(-(term1/term2)**M)

        elif mode == 'cCED':  # conservative coherence enhancing diffusion
            mu = np.ones(eigvals.shape) * ALPHA
            term1 = LAMBDA + eigvals[:, 0:2]
            term2 = eigvals[:, 2, None] - eigvals[:, 0:2]
            mu[:, 0:2] = ALPHA + c * np.exp(-(term1/term2)**M)

    else:
        mu = np.ones(eigvals.shape)
        print('    Invalid smoothing mesthod. Weights are all set to ones.')

    return mu


def construct_diffusion_tensors(eigvecs, weights):
    """Vectorized consruction of diffusion tensors."""
    dims = eigvecs.shape
    D = np.zeros(dims[:-2] + (dims[-1], dims[-1]))
    for i in range(dims[-1]):  # weight vectors
        D += weights[:, i, None, None] * self_outer_product(eigvecs[..., i])
    return D


def smooth_matrix_image(matrix_image, RHO=0):
    """Gaussian smoothing applied to matrix image."""
    if RHO == 0:
        return matrix_image
    else:
        dims = matrix_image.shape
        for x in range(dims[-2]):
            for y in range(dims[-1]):
                gaussian_filter(matrix_image[..., x, y], sigma=RHO,
                                mode='nearest',
                                output=matrix_image[..., x, y])
        return matrix_image