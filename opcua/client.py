import sys
import asyncio
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QProgressBar, 
                           QDoubleSpinBox)
from PyQt5.QtCore import QTimer
from asyncua import Client, Node, ua  

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s | %(message)s',
                   datefmt='%H:%M:%S')
_logger = logging.getLogger('asyncua')
logging.getLogger("asyncua").setLevel(logging.WARNING)  # 불필요한 로그 감춤

class AirConditionerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("에어컨 제어 시스템")
        self.setMinimumSize(600, 400)
        
        # 메인 위젯과 레이아웃
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 상태 표시 영역
        status_layout = QHBoxLayout()
        
        # 온도 게이지
        temp_layout = QVBoxLayout()
        self.temp_label = QLabel("현재 온도: --°C")
        self.temp_gauge = QProgressBar()
        self.temp_gauge.setRange(0, 400)  # 0~40도를 0~400으로 표시
        temp_layout.addWidget(self.temp_label)
        temp_layout.addWidget(self.temp_gauge)
        
        # 습도 게이지
        humidity_layout = QVBoxLayout()
        self.humidity_label = QLabel("현재 습도: --%")
        self.humidity_gauge = QProgressBar()
        self.humidity_gauge.setRange(0, 100)
        humidity_layout.addWidget(self.humidity_label)
        humidity_layout.addWidget(self.humidity_gauge)
        
        status_layout.addLayout(temp_layout)
        status_layout.addLayout(humidity_layout)
        
        # 전력 사용량과 전기 요금
        power_layout = QHBoxLayout()
        self.power_label = QLabel("전력 사용량: -- kWh")
        self.cost_label = QLabel("전기 요금: -- 원")
        power_layout.addWidget(self.power_label)
        power_layout.addWidget(self.cost_label)
        
        # 제어 영역
        control_layout = QHBoxLayout()
        
        # 전원 버튼
        self.power_button = QPushButton("전원 OFF")
        self.power_button.setCheckable(True)
        self.power_button.clicked.connect(self.on_power_clicked)
        
        # 온도 설정
        temp_control_layout = QHBoxLayout()
        self.temp_spinbox = QDoubleSpinBox()
        self.temp_spinbox.setRange(18, 30)
        self.temp_spinbox.setValue(24)
        self.temp_spinbox.setSingleStep(0.5)
        self.set_temp_button = QPushButton("온도 설정")
        self.set_temp_button.clicked.connect(self.on_temp_clicked)
        temp_control_layout.addWidget(QLabel("목표 온도:"))
        temp_control_layout.addWidget(self.temp_spinbox)
        temp_control_layout.addWidget(self.set_temp_button)
        
        control_layout.addWidget(self.power_button)
        control_layout.addLayout(temp_control_layout)
        
        # 레이아웃 조합
        layout.addLayout(status_layout)
        layout.addLayout(power_layout)
        layout.addLayout(control_layout)
        
        # OPC UA 클라이언트 설정
        self.client = None
        self.subscription = None
        self.nodes = {}
        
        # 초기 연결
        self.initialize_connection()

    def initialize_connection(self):
        asyncio.create_task(self.setup_client())

    async def setup_client(self):
        try:
            _logger.info("서버에 연결 시도 중...")
            self.client = Client("opc.tcp://localhost:4840/freeopcua/server/")
            await self.client.connect()
            
            # namespace 인덱스 가져오기
            uri = "http://examples.freeopcua.github.io"
            idx = await self.client.get_namespace_index(uri)
            
            # 노드 가져오기 - 수정된 부분
            self.nodes['Power'] = await self.client.nodes.root.get_child(
                ["0:Objects", f"{idx}:AirConditioner", f"{idx}:Power"]
            )
            self.nodes['TargetTemperature'] = await self.client.nodes.root.get_child(
                ["0:Objects", f"{idx}:AirConditioner", f"{idx}:TargetTemperature"]
            )
            
            # Power 노드 데이터 타입 확인
            power_node = self.nodes['Power']
            current_power = await power_node.read_value()
            _logger.info(f"Initial power state: {current_power}")
            
            # 현재 전원 상태 확인 및 버튼 상태 동기화
            self.power_button.setChecked(current_power)
            self.power_button.setText("전원 ON" if current_power else "전원 OFF")
            
            # 모니터링 노드들도 같은 방식으로 접근
            temp_node = await self.client.nodes.root.get_child(
                ["0:Objects", f"{idx}:AirConditioner", f"{idx}:CurrentTemperature"]
            )
            humidity_node = await self.client.nodes.root.get_child(
                ["0:Objects", f"{idx}:AirConditioner", f"{idx}:Humidity"]
            )
            power_usage_node = await self.client.nodes.root.get_child(
                ["0:Objects", f"{idx}:AirConditioner", f"{idx}:PowerUsage"]
            )
            cost_node = await self.client.nodes.root.get_child(
                ["0:Objects", f"{idx}:AirConditioner", f"{idx}:ElectricityCost"]
            )
            
            # 구독 설정
            self.subscription = await self.client.create_subscription(500, self)
            nodes_to_monitor = [temp_node, humidity_node, power_usage_node, cost_node, self.nodes['Power']]
            await self.subscription.subscribe_data_change(nodes_to_monitor)
            
            _logger.info("서버 연결 및 모니터링 설정 완료")
            
        except Exception as e:
            _logger.error(f"연결 오류: {e}", exc_info=True)

    async def datachange_notification(self, node: Node, val, data):
        try:
            name = (await node.read_browse_name()).Name
            if name == "CurrentTemperature":
                self.temp_label.setText(f"현재 온도: {val:.1f}°C")
                self.temp_gauge.setValue(int(val * 10))
            elif name == "Humidity":
                self.humidity_label.setText(f"현재 습도: {val:.1f}%")
                self.humidity_gauge.setValue(int(val))
            elif name == "PowerUsage":
                self.power_label.setText(f"전력 사용량: {val:.2f} kWh")
            elif name == "ElectricityCost":
                self.cost_label.setText(f"전기 요금: {int(val):,} 원")
            elif name == "Power":
                self.power_button.setChecked(val)
                self.power_button.setText("전원 ON" if val else "전원 OFF")
        except Exception as e:
            _logger.error(f"데이터 업데이트 오류: {e}", exc_info=True)

    def on_power_clicked(self):
        asyncio.create_task(self.toggle_power())

    def on_temp_clicked(self):
        asyncio.create_task(self.set_temperature())

    async def toggle_power(self):
        if self.nodes.get('Power'):
            is_on = self.power_button.isChecked()
            try:
                _logger.info(f"전원 상태 변경 시도: {is_on}")
                # 현재 상태 확인
                current = await self.nodes['Power'].read_value()
                _logger.info(f"Current power state: {current}")
                
                # 상태 변경
                await self.nodes['Power'].write_value(is_on)
                
                # 변경 후 상태 확인
                new_state = await self.nodes['Power'].read_value()
                _logger.info(f"New power state: {new_state}")
                
                self.power_button.setText("전원 ON" if new_state else "전원 OFF")
                self.power_button.setChecked(new_state)
            except Exception as e:
                _logger.error(f"전원 제어 오류: {e}", exc_info=True)
                self.power_button.setChecked(not is_on)
                self.power_button.setText("전원 ON" if not is_on else "전원 OFF")

    async def set_temperature(self):
        if self.nodes.get('TargetTemperature'):
            temp = self.temp_spinbox.value()
            try:
                _logger.info(f"목표 온도 설정: {temp}°C")
                await self.nodes['TargetTemperature'].write_value(temp)
                _logger.info(f"목표 온도 설정 완료: {temp}°C")
            except Exception as e:
                _logger.error(f"온도 설정 오류: {e}", exc_info=True)

    async def closeEvent(self, event):
        if self.subscription:
            await self.subscription.delete()
        if self.client:
            await self.client.disconnect()
        event.accept()

async def main():
    app = QApplication(sys.argv)
    window = AirConditionerGUI()
    window.show()
    
    while True:
        app.processEvents()
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        _logger.error(f"프로그램 오류: {e}", exc_info=True)