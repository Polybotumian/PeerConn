from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout

class ConnectionDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('IP and Port Info')

        self.layout = QVBoxLayout(self)

        self.ipLabel = QLabel("IP Address:", self)
        self.ipLineEdit = QLineEdit(self)

        self.portLabel = QLabel("Port:", self)
        self.portLineEdit = QLineEdit(self)

        self.connectButton = QPushButton("Connect", self)
        self.connectButton.clicked.connect(self.accept)

        self.layout.addWidget(self.ipLabel)
        self.layout.addWidget(self.ipLineEdit)
        self.layout.addWidget(self.portLabel)
        self.layout.addWidget(self.portLineEdit)
        self.layout.addWidget(self.connectButton)

    def get_data(self):
        return self.ipLineEdit.text(), self.portLineEdit.text()