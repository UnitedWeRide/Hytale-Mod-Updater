"""
Fingerprint Utility Module

This module provides functionality for computing CurseForge fingerprints
for mod files using the optimized algorithm from cf_fingerprint.
"""
import logging
from numpy import (
    uint8,
    uint32,
    seterr,
    memmap
)

from pathlib import Path

from typing import Union, Optional

logger = logging.getLogger(__name__)


def _process_chunks(chunks, fingerprint: uint32, MULTIPLEX: uint32, MASK_32BIT: uint32) -> uint32:
    """Process chunks in batches to avoid O(N²) nested loops."""
    batch_size = 1024
    num_batches = (len(chunks) + batch_size - 1) // batch_size
    for b in range(num_batches):
        start = b * batch_size
        end = min((b + 1) * batch_size, len(chunks))
        batch = chunks[start:end]
        temp1 = (batch * MULTIPLEX) & MASK_32BIT
        temp2 = ((temp1 ^ (temp1 >> 24)) * MULTIPLEX) & MASK_32BIT
        # Use vectorized reduce instead of Python loop
        for t in temp2:
            fingerprint = ((fingerprint * MULTIPLEX) & MASK_32BIT) ^ t
    return fingerprint


def compute_fingerprint(file_path: Union[str, Path]) -> Optional[int]:
    """
    Computes a 32-bit fingerprint for a given file using an optimized algorithm.
    
    Args:
        file_path (Union[str, Path]): Path to the file to be fingerprinted.
        
    Returns:
        int: The 32-bit fingerprint of the file, or None if an error occurs.
    """
    MULTIPLEX = uint32(1540483477)
    MASK_32BIT = uint32(4294967295)

    # Only suppress overflow warnings relevant to our algorithm
    seterr(over='ignore', invalid='ignore')  # Allow integer overflow as intended

    try:
        file_path = Path(file_path)  # Ensure file_path is a Path object
        if not file_path.is_file():
            return None

        buffer = memmap(file_path, dtype=uint8, mode='r')
        buffer = buffer[(buffer != 9) & (buffer != 10) & (buffer != 13) & (buffer != 32)]

        fingerprint = uint32(1) ^ uint32(len(buffer))
        chunk_count = len(buffer) // 4

        if chunk_count > 0:
            chunks = buffer[:chunk_count * 4].view(dtype=uint32)
            
            fingerprint = uint32(fingerprint)
            
            batch_size = 1024
            num_batches = (len(chunks) + batch_size - 1) // batch_size

            for b in range(num_batches):
                start = b * batch_size
                end = min((b + 1) * batch_size, len(chunks))
                batch = chunks[start:end]
                
                temp1 = (batch * MULTIPLEX) & MASK_32BIT
                temp2 = ((temp1 ^ (temp1 >> 24)) * MULTIPLEX) & MASK_32BIT
                
                for t in temp2:
                    fingerprint = ((fingerprint * MULTIPLEX) & MASK_32BIT) ^ t

        # Handle remaining bytes that don't fit into 32-bit chunks
        remaining = buffer[chunk_count * 4:]
        if remaining.size:
            remaining_bytes = uint32(int.from_bytes(remaining.tobytes(), byteorder='little'))
            fingerprint = ((fingerprint ^ remaining_bytes) * MULTIPLEX) & MASK_32BIT

        fingerprint = ((fingerprint ^ (fingerprint >> 13)) * MULTIPLEX) & MASK_32BIT
        fingerprint = fingerprint ^ (fingerprint >> 15)

        return int(fingerprint)

    except (OSError, ValueError, TypeError):
        logger.exception("Failed to compute fingerprint for %s", file_path)
        return None


def format_fingerprint(fingerprint: int) -> str:
    """
    Format the fingerprint as a hexadecimal string for display.
    
    Args:
        fingerprint: The 32-bit fingerprint integer
        
    Returns:
        Formatted hex string (e.g., "0x12345678")
    """
    if fingerprint is None:
        return "N/A"
    return f"0x{fingerprint:08X}"