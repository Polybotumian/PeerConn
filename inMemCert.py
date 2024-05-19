import os
from OpenSSL.crypto import PKey, X509, TYPE_RSA, X509Extension
from OpenSSL.SSL import TLSv1_2_METHOD
from twisted.internet.ssl import CertificateOptions


def generateCa() -> tuple[PKey, X509]:
    ca_key = PKey()
    ca_key.generate_key(TYPE_RSA, 2048)

    ca_cert = X509()
    ca_cert.get_subject().C = "TR"
    ca_cert.get_subject().ST = "Istanbul"
    ca_cert.get_subject().L = "Center"
    ca_cert.get_subject().O = "My Custom CA"
    ca_cert.get_subject().CN = "My Custom CA Root Certificate"
    ca_cert.set_serial_number(
        int.from_bytes(os.urandom(16), byteorder="big")
    )
    ca_cert.gmtime_adj_notBefore(0)
    ca_cert.gmtime_adj_notAfter(24 * 60 * 60)  # 24 Hours
    ca_cert.set_issuer(ca_cert.get_subject())
    ca_cert.set_pubkey(ca_key)
    ca_cert.add_extensions(
        [
            X509Extension(b"basicConstraints", True, b"CA:TRUE, pathlen:0"),
            X509Extension(b"keyUsage", True, b"keyCertSign, cRLSign"),
            X509Extension(b"subjectKeyIdentifier", False, b"hash", subject=ca_cert),
        ]
    )
    ca_cert.sign(ca_key, "sha256")

    return ca_key, ca_cert


def genCrtAndKey(ca_key: PKey, ca_cert: X509) -> CertificateOptions:
    key = PKey()
    key.generate_key(TYPE_RSA, 2048)

    cert = X509()
    cert.get_subject().C = "TR"
    cert.get_subject().ST = "Istanbul"
    cert.get_subject().L = "Center"
    cert.get_subject().O = "No Company"
    cert.get_subject().CN = "No Company Address"
    cert.set_serial_number(int.from_bytes(os.urandom(16), byteorder="big"))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(24 * 60 * 60)  # 24 Hours
    cert.set_issuer(ca_cert.get_subject())
    cert.set_pubkey(key)
    cert.add_extensions(
        [
            X509Extension(b"keyUsage", True, b"digitalSignature, keyEncipherment"),
            X509Extension(b"extendedKeyUsage", True, b"serverAuth"),
        ]
    )
    cert.sign(ca_key, "sha256")

    return CertificateOptions(privateKey=key, certificate=cert, method=TLSv1_2_METHOD)
