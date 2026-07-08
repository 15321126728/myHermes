"""Accelerated maximal square using a compiled C extension."""

import os
import sys
import numpy as np

# Locate the compiled C extension
_lib_dir = os.path.dirname(os.path.abspath(__file__))
_ext_path = os.path.join(_lib_dir, '_maxsquare.so')

if os.path.exists(_ext_path):
    if _lib_dir not in sys.path:
        sys.path.insert(0, _lib_dir)
    from _maxsquare import maximal_square as _maximal_square_impl
elif os.path.exists('/app/_maxsquare.so'):
    if '/app' not in sys.path:
        sys.path.insert(0, '/app')
    from _maxsquare import maximal_square as _maximal_square_impl
else:
    # Fallback: use Numba if C extension not found
    from numba import njit

    @njit(cache=True, fastmath=True)
    def _maximal_square_impl(matrix: np.ndarray) -> int:
        """Numba-accelerated maximal square using 1D DP."""
        rows, cols = matrix.shape
        if rows == 0 or cols == 0:
            return 0
        dp = np.zeros(cols + 1, dtype=np.int64)
        maxsqlen = 0
        for i in range(rows):
            prev = 0
            for j in range(cols):
                temp = dp[j + 1]
                if matrix[i, j]:
                    cur = prev
                    v = dp[j]
                    if v < cur:
                        cur = v
                    v = dp[j + 1]
                    if v < cur:
                        cur = v
                    val = cur + 1
                    dp[j + 1] = val
                    if val > maxsqlen:
                        maxsqlen = val
                else:
                    dp[j + 1] = 0
                prev = temp
        return maxsqlen * maxsqlen


def maximal_square(matrix: np.ndarray) -> int:
    """Find the area of the largest square of 1s in a binary matrix.

    Uses a highly optimized C implementation (or Numba fallback)
    for maximum CPU performance. Suitable for large matrices (1000x1000+).

    Args:
        matrix: A numpy ndarray containing only 0s and 1s.

    Returns:
        The area (side^2) of the largest square containing only 1s.
    """
    if matrix.size == 0:
        return 0
    return _maximal_square_impl(matrix)
