import os
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from twisted.internet.ssl import CertificateOptions, PrivateCertificate
from OpenSSL import crypto, SSL
from ipaddress import ip_address
import logging

logging.basicConfig(level=logging.INFO)

def is_certificate_valid(cert_path: str) -> bool:
    if not os.path.exists(cert_path):
        return False
    try:
        with open(cert_path, "rb") as cert_file:
            cert_data = cert_file.read()
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
        not_after = cert.get_notAfter().decode("ascii")
        expiry_date = datetime.strptime(not_after, "%Y%m%d%H%M%SZ")
        return datetime.utcnow() < expiry_date
    except Exception as e:
        logging.error(f"Error validating certificate: {e}")
        return False

def generateCa() -> tuple:
    if is_certificate_valid("ca.crt") and os.path.exists("ca.key"):
        with open("ca.key", "rb") as key_file:
            ca_key = serialization.load_pem_private_key(
                key_file.read(), password=None)
        with open("ca.crt", "rb") as cert_file:
            ca_cert = x509.load_pem_x509_certificate(cert_file.read())
        return ca_key, ca_cert

    ca_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=3072,  # Using larger key size for better security
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"TR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Istanbul"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Center"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"My Custom CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"My Custom CA Root Certificate"),
    ])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(key_cert_sign=True, crl_sign=True, digital_signature=False, content_commitment=False, key_encipherment=False, data_encipherment=False, key_agreement=False, encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    with open("ca.key", "wb") as key_file:
        key_file.write(ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open("ca.crt", "wb") as cert_file:
        cert_file.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    logging.info("CA certificate and key generated.")
    return ca_key, ca_cert

def genCrtAndKey(ca_key, ca_cert) -> CertificateOptions:
    if is_certificate_valid("server.crt") and os.path.exists("server.key"):
        with open("server.key", "rb") as key_file:
            key = serialization.load_pem_private_key(
                key_file.read(), password=None)
        with open("server.crt", "rb") as cert_file:
            cert = x509.load_pem_x509_certificate(cert_file.read())
        pkey = crypto.PKey.from_cryptography_key(key)
        x509_cert = crypto.X509.from_cryptography(cert)
        x509_ca_cert = crypto.X509.from_cryptography(ca_cert)
        return CertificateOptions(
            privateKey=pkey,
            certificate=x509_cert,
            extraCertChain=[x509_ca_cert],
            method=SSL.TLS_METHOD,
        )

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=3072,  # Using larger key size for better security
    )

    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"TR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Istanbul"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Center"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"No Company"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"No Company Address"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=True, key_cert_sign=False, crl_sign=False, content_commitment=False, data_encipherment=False, key_agreement=False, encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]), critical=True)  # Added client authentication for comprehensive use
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(u"localhost"), x509.IPAddress(ip_address("127.0.0.1"))]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    with open("server.key", "wb") as key_file:
        key_file.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open("server.crt", "wb") as cert_file:
        cert_file.write(cert.public_bytes(serialization.Encoding.PEM))

    with open("server-chain.crt", "wb") as chain_file:
        chain_file.write(cert.public_bytes(serialization.Encoding.PEM))
        chain_file.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    logging.info("Server certificate and key generated.")

    # Convert certificates to PyOpenSSL objects
    pkey = crypto.PKey.from_cryptography_key(key)
    x509_cert = crypto.X509.from_cryptography(cert)
    x509_ca_cert = crypto.X509.from_cryptography(ca_cert)

    # Create a context factory and set ciphers
    contextFactory = SSL.Context(SSL.TLS_METHOD)
    contextFactory.use_certificate(x509_cert)
    contextFactory.use_privatekey(pkey)
    contextFactory.add_extra_chain_cert(x509_ca_cert)
    contextFactory.set_cipher_list(b'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-RSA-AES128-GCM-SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256')

    return CertificateOptions(
        privateKey=pkey,
        certificate=x509_cert,
        extraCertChain=[x509_ca_cert],
        method=SSL.TLS_METHOD,
    )