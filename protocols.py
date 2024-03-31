from twisted.internet import protocol
from signals import Communication, PeerInfo
from dtos import PDTO
from uuid import uuid4

class P2PProtocol(protocol.Protocol):
    def __init__(self, communication, peerInfo):
        self.identifier = str(uuid4())
        self.communication: Communication = communication
        self.communication.send.connect(self.send_message)
        self.communication.close.connect(self.close_connection)
        self.peerInfo: PeerInfo = peerInfo

    def connectionMade(self):
        print("Bağlantı kuruldu")
        self.authenticatePeer()

    def connectionLost(self, reason):
        print(f"Bağlantı kesildi!{reason.getErrorMessage()}")

    def close_connection(self, identifier):
        if self.identifier == identifier:
            print("Bağlantı kapatılıyor...")
            self.transport.loseConnection()

    def dataReceived(self, data):
        if data.startswith(b""):
            self.handle_message(data)
        elif data.startswith(b"file:"):
            self.handle_file(data[5:])
        else:
            print("Tanımlanamayan veri tipi aldı.")

    def send_message(self, identifier, message):
        if message and self.identifier == identifier:
            # Mesajı byte olarak kodlayın
            encoded_message = message.encode('utf-8')

            # Ağ üzerinden mesajı gönder
            self.transport.write(encoded_message)
            print(f"Gönderilen mesaj: {message}")

    def handle_message(self, message):
        self.communication.received.emit(self.identifier, message.decode('utf-8'))
        print(f"Mesaj alındı: {message.decode('utf-8')}")

    def handle_file(self, file_data):
        print(f"Dosya alındı: {len(file_data)} bytes")

    def authenticatePeer(self):
        # Peer kimlik doğrulama işlemleri
        basicPeerInfo = PDTO()
        basicPeerInfo.identifier = self.identifier
        basicPeerInfo.flags = 1
        self.peerInfo.descriptive.emit(basicPeerInfo)
        print("Peer doğrulanıyor...")

    def handleError(self, error):
        # Hata yönetimi
        print(f"Hata oluştu: {error}")

    def encryptData(self, data):
        # Veri şifreleme işlemleri
        return data  # Örnek olarak, şimdilik veriyi olduğu gibi döndür

    def decryptData(self, data):
        # Veri şifre çözme işlemleri
        return data  # Örnek olarak, şimdilik veriyi olduğu gibi döndür