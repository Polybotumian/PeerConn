import os
from datetime import datetime
from OpenSSL.crypto import (
    PKey,
    X509,
    TYPE_RSA,
    X509Extension,
    dump_privatekey,
    dump_certificate,
    load_privatekey,
    load_certificate,
    FILETYPE_PEM,
)
from OpenSSL.SSL import TLSv1_2_METHOD
from twisted.internet.ssl import CertificateOptions


def is_certificate_valid(cert_path: str) -> bool:
    if not os.path.exists(cert_path):
        return False
    with open(cert_path, "rb") as cert_file:
        cert_data = cert_file.read()
    cert = load_certificate(FILETYPE_PEM, cert_data)
    not_after = cert.get_notAfter().decode("ascii")
    expiry_date = datetime.strptime(not_after, "%Y%m%d%H%M%SZ")
    return datetime.utcnow() < expiry_date


def generateCa() -> tuple[PKey, X509]:
    """
    Generates a Certificate Authority (CA) with a private key and certificate.

    Returns:
        tuple: A tuple containing the CA's private key and certificate.
    """
    if is_certificate_valid("ca.crt") and os.path.exists("ca.key"):
        with open("ca.key", "rb") as key_file:
            ca_key = load_privatekey(FILETYPE_PEM, key_file.read())
        with open("ca.crt", "rb") as cert_file:
            ca_cert = load_certificate(FILETYPE_PEM, cert_file.read())
        return ca_key, ca_cert

    ca_key = PKey()
    ca_key.generate_key(TYPE_RSA, 2048)  # Generate RSA key with 2048-bit length

    ca_cert = X509()
    ca_cert.get_subject().C = "TR"  # Country
    ca_cert.get_subject().ST = "Istanbul"  # State
    ca_cert.get_subject().L = "Center"  # Locality
    ca_cert.get_subject().O = "My Custom CA"  # Organization
    ca_cert.get_subject().CN = "My Custom CA Root Certificate"  # Common Name
    ca_cert.set_serial_number(
        int.from_bytes(os.urandom(16), byteorder="big")
    )  # Serial number
    ca_cert.gmtime_adj_notBefore(0)  # Valid from now
    ca_cert.gmtime_adj_notAfter(24 * 60 * 60)  # Valid for 24 hours
    ca_cert.set_issuer(ca_cert.get_subject())  # Self-signed
    ca_cert.set_pubkey(ca_key)  # Set public key
    ca_cert.add_extensions(
        [
            X509Extension(
                b"basicConstraints", True, b"CA:TRUE, pathlen:0"
            ),  # Basic constraints
            X509Extension(b"keyUsage", True, b"keyCertSign, cRLSign"),  # Key usage
            X509Extension(
                b"subjectKeyIdentifier", False, b"hash", subject=ca_cert
            ),  # Subject key identifier
        ]
    )
    ca_cert.sign(ca_key, "sha256")  # Sign the certificate with its own key

    # Save CA key and certificate to files
    with open("ca.key", "wb") as key_file:
        key_file.write(dump_privatekey(FILETYPE_PEM, ca_key))
    with open("ca.crt", "wb") as cert_file:
        cert_file.write(dump_certificate(FILETYPE_PEM, ca_cert))

    return ca_key, ca_cert


def genCrtAndKey(ca_key: PKey, ca_cert: X509) -> CertificateOptions:
    """
    Generates a server certificate signed by the provided CA.

    Args:
        ca_key (PKey): The CA's private key.
        ca_cert (X509): The CA's certificate.

    Returns:
        CertificateOptions: The server certificate options for use with Twisted.
    """
    if is_certificate_valid("server.crt") and os.path.exists("server.key"):
        with open("server.key", "rb") as key_file:
            key = load_privatekey(FILETYPE_PEM, key_file.read())
        with open("server.crt", "rb") as cert_file:
            cert = load_certificate(FILETYPE_PEM, cert_file.read())
        return CertificateOptions(
            privateKey=key,
            certificate=cert,
            extraCertChain=[ca_cert],
            method=TLSv1_2_METHOD,
        )

    key = PKey()
    key.generate_key(TYPE_RSA, 2048)  # Generate RSA key with 2048-bit length

    cert = X509()
    cert.get_subject().C = "TR"  # Country
    cert.get_subject().ST = "Istanbul"  # State
    cert.get_subject().L = "Center"  # Locality
    cert.get_subject().O = "No Company"  # Organization
    cert.get_subject().CN = "No Company Address"  # Common Name
    cert.set_serial_number(
        int.from_bytes(os.urandom(16), byteorder="big")
    )  # Serial number
    cert.gmtime_adj_notBefore(0)  # Valid from now
    cert.gmtime_adj_notAfter(24 * 60 * 60)  # Valid for 24 hours
    cert.set_issuer(ca_cert.get_subject())  # Issuer is the CA
    cert.set_pubkey(key)  # Set public key
    cert.add_extensions(
        [
            X509Extension(
                b"keyUsage", True, b"digitalSignature, keyEncipherment"
            ),  # Key usage
            X509Extension(
                b"extendedKeyUsage", True, b"serverAuth"
            ),  # Extended key usage
        ]
    )
    cert.sign(ca_key, "sha256")  # Sign the certificate with the CA's key

    # Save server key and certificate to files
    with open("server.key", "wb") as key_file:
        key_file.write(dump_privatekey(FILETYPE_PEM, key))
    with open("server.crt", "wb") as cert_file:
        cert_file.write(dump_certificate(FILETYPE_PEM, cert))

    # Create chain file
    with open("server-chain.crt", "wb") as chain_file:
        chain_file.write(dump_certificate(FILETYPE_PEM, cert))
        chain_file.write(dump_certificate(FILETYPE_PEM, ca_cert))

    return CertificateOptions(
        privateKey=key,
        certificate=cert,
        extraCertChain=[ca_cert],
        method=TLSv1_2_METHOD,
    )
