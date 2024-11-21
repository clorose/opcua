# client.py
import sys
import asyncio
import logging
from asyncua import Client
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel

_logger = logging.getLogger(__name__)

class SubscriptionHandler:
    def __init__(self, label):
        self.label = label
        
    async def datachange_notification(self, node, val, data):
        _logger.info("Counter changed to: %s", val)
        self.label.setText(f"Count: {val}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = None
        self.counter_var = None
        self.subscription = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Counter Client")
        self.setGeometry(100, 100, 200, 150)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.count_label = QLabel("Count: 0")
        layout.addWidget(self.count_label)

        red_button = QPushButton("Red Button")
        red_button.setStyleSheet("background-color: red; color: white;")
        red_button.clicked.connect(self.increment_counter)
        layout.addWidget(red_button)

        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset_counter)
        layout.addWidget(reset_button)

        asyncio.create_task(self.connect_opcua())

    async def connect_opcua(self):
        try:
            url = "opc.tcp://localhost:4840/freeopcua/server/"
            self.client = Client(url=url)
            await self.client.connect()
            
            # namespace 인덱스 찾기
            uri = "http://examples.freeopcua.github.io"
            idx = await self.client.get_namespace_index(uri)
            
            # 정확한 node path로 counter 변수 찾기
            self.counter_var = await self.client.nodes.root.get_child(
                [f"0:Objects", f"{idx}:MyObject", f"{idx}:Counter"]
            )
            
            # 구독 설정
            handler = SubscriptionHandler(self.count_label)
            self.subscription = await self.client.create_subscription(500, handler)
            await self.subscription.subscribe_data_change([self.counter_var])
            
            # 초기값 표시
            value = await self.counter_var.read_value()
            self.count_label.setText(f"Count: {value}")
            _logger.info("Connected to OPC UA server")
            
        except Exception as e:
            _logger.error("Connection failed: %s", e)

    def increment_counter(self):
        if self.counter_var:
            asyncio.create_task(self.do_increment())

    async def do_increment(self):
        try:
            current = await self.counter_var.read_value()
            await self.counter_var.write_value(current + 1)
        except Exception as e:
            _logger.error("Failed to increment: %s", e)

    def reset_counter(self):
        if self.counter_var:
            asyncio.create_task(self.do_reset())

    async def do_reset(self):
        try:
            await self.counter_var.write_value(0)
        except Exception as e:
            _logger.error("Failed to reset: %s", e)

async def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    while True:
        app.processEvents()
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%H:%M:%S')
    logging.getLogger("asyncua").setLevel(logging.WARNING)
    asyncio.run(main())