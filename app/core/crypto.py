"""Dechiffrement des trames Arduino chiffrees en AES (comme la Azure Function).

La passerelle transmet {"data": "<base64>"} ; le base64 contient le message
chiffre. On tente CBC (IV 16 octets) puis GCM en repli, pour "gerer tout".
Clef/IV lus depuis la config (HEX), identiques a AES_KEY / AES_IV cote Azure.
"""
from __future__ import annotations

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

_KEY = bytes.fromhex(settings.aes_key_hex)
_IV = bytes.fromhex(settings.aes_iv_hex)


def _try_cbc(ciphertext: bytes) -> bytes | None:
    """AES-CBC + retrait du padding PKCS7. None si ca ne colle pas."""
    if len(ciphertext) == 0 or len(ciphertext) % 16 != 0:
        return None
    try:
        decryptor = Cipher(algorithms.AES(_KEY), modes.CBC(_IV)).decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()
    except Exception:
        return None


def _try_gcm(ciphertext: bytes) -> bytes | None:
    """AES-GCM (repli) : nonce = IV, tag concatene en fin de message."""
    try:
        return AESGCM(_KEY).decrypt(_IV, ciphertext, None)
    except Exception:
        return None


def decrypt_frame(ciphertext: bytes) -> bytes | None:
    """Dechiffre une trame AES : essaie CBC puis GCM. None si echec total."""
    return _try_cbc(ciphertext) or _try_gcm(ciphertext)
