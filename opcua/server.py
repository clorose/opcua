import asyncio
import logging
from asyncua import ua, Server
from asyncua.common.callback import CallbackType

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('asyncua')

class SubscriptionHandler:
    """서버 사이드 subscription 핸들러"""
    async def datachange_notification(self, node, val, data):
        try:
            name = (await node.read_browse_name()).Name
            _logger.info("DataChange: %s = %s", name, val)
        except Exception as e:
            _logger.error("Error in datachange_notification: %s", e)

def create_monitored_items(event, dispatcher):
    """클라이언트가 모니터링 항목을 생성할 때 호출"""
    for idx in range(len(event.response_params)):
        if event.response_params[idx].StatusCode.is_good():
            nodeId = event.request_params.ItemsToCreate[idx].ItemToMonitor.NodeId
            _logger.info("Client started monitoring: %s", nodeId)

def delete_monitored_items(event, dispatcher):
    """클라이언트가 모니터링을 중단할 때 호출"""
    _logger.info("Client stopped monitoring items")

async def main():
    server = Server()
    await server.init()
    
    # 서버 설정
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    server.set_server_name("Air Conditioner Control Server")
    
    # 보안 정책 설정 (테스트용으로 NoSecurity만 사용)
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

    # namespace 설정
    uri = "http://examples.freeopcua.github.io"
    idx = await server.register_namespace(uri)

    # 에어컨 시스템 객체 생성
    ac_system = await server.nodes.objects.add_object(idx, "AirConditioner")
    
    # 제어 변수 (클라이언트에서 조작 가능)
    power = await ac_system.add_variable(idx, "Power", False)
    await power.set_writable()
    target_temp = await ac_system.add_variable(idx, "TargetTemperature", 24.0)
    await target_temp.set_writable()
    
    # 모니터링 변수들 (읽기 전용)
    current_temp = await ac_system.add_variable(idx, "CurrentTemperature", 35.0)
    humidity = await ac_system.add_variable(idx, "Humidity", 80.0)
    power_usage = await ac_system.add_variable(idx, "PowerUsage", 0.0)
    electricity_cost = await ac_system.add_variable(idx, "ElectricityCost", 0)
    current_rate = await ac_system.add_variable(idx, "CurrentRate", 93.3)
    operation_time = await ac_system.add_variable(idx, "OperationTime", 0)

    # 이벤트 타입 생성
    etype = await server.create_custom_event_type(
        idx, 
        "ACStateChange",
        ua.ObjectIds.BaseEventType,
        [
            ("CurrentTemperature", ua.VariantType.Double),
            ("TargetTemperature", ua.VariantType.Double),
            ("PowerState", ua.VariantType.Boolean)
        ]
    )
    
    # 이벤트 생성기 설정
    evgen = await server.get_event_generator(etype, ac_system)

    def calculate_progressive_rate(usage):
        if usage <= 200:
            return 93.3
        elif usage <= 400:
            return 187.9
        else:
            return 280.6

    # 콜백 등록
    server.subscribe_server_callback(CallbackType.ItemSubscriptionCreated, create_monitored_items)
    server.subscribe_server_callback(CallbackType.ItemSubscriptionDeleted, delete_monitored_items)

    # 서버 사이드 subscription 설정
    handler = SubscriptionHandler()
    subscription = await server.create_subscription(500, handler)
    await subscription.subscribe_data_change([power, target_temp, current_temp, humidity, power_usage])

    async with server:
        _logger.info("Air Conditioner Control Server started at opc.tcp://0.0.0.0:4840")
        
        while True:
            try:
                is_power_on = await power.read_value()
                target = await target_temp.read_value()
                temp = await current_temp.read_value()
                hum = await humidity.read_value()
                usage = await power_usage.read_value()
                time = await operation_time.read_value()
                
                if is_power_on:
                    # 온도 제어 - 냉방 효율 향상
                    temp_diff = temp - target
                    if temp_diff > 0:
                        cooling_rate = min(1.5, temp_diff * 0.4)  # 냉방 효율 증가
                        new_temp = max(target, temp - cooling_rate)
                        await current_temp.write_value(round(new_temp, 1))
                    
                    # 습도 제어 - 더 빠른 제습
                    if hum > 40.0:  # 목표 습도를 40%로 낮춤
                        dehumidify_rate = 3.0 if hum > 60 else 2.0  # 습도가 높을 때 더 빠른 제습
                        new_humidity = max(40.0, hum - dehumidify_rate)
                        await humidity.write_value(round(new_humidity, 1))
                    
                    # 전력 사용량 계산 - 보정
                    base_power = 3.0  # 기본 소비전력 증가
                    temp_addition = temp_diff * 0.4  # 온도차에 따른 전력소비 증가
                    heat_penalty = max(0, (temp - 35) * 0.3)
                    humidity_addition = max(0, (hum - 50) * 0.02)  # 습도에 따른 추가 전력소비
                    power_rate = base_power + temp_addition + heat_penalty + humidity_addition
                    
                    new_usage = usage + (power_rate / 60)  # 분당 소비전력으로 변경
                    await power_usage.write_value(round(new_usage, 2))
                    
                    # 누진세 계산
                    rate = calculate_progressive_rate(new_usage)
                    await current_rate.write_value(rate)
                    new_cost = int(new_usage * rate)
                    await electricity_cost.write_value(new_cost)
                    
                    # 가동시간 증가
                    await operation_time.write_value(time + 1)
                    
                    # 상태 변경 이벤트 발생
                    evgen.event.Message = ua.LocalizedText(f"Temperature: {new_temp:.1f}°C")
                    evgen.event.Severity = 100 if temp_diff > 5 else 50
                    evgen.event.CurrentTemperature = new_temp
                    evgen.event.TargetTemperature = target
                    evgen.event.PowerState = True
                    await evgen.trigger()
                    
                else:  # 에어컨 꺼짐
                    if temp < 40.0:
                        new_temp = min(40.0, temp + 0.3)
                        await current_temp.write_value(round(new_temp, 1))
                    
                    if hum < 85.0:
                        new_humidity = min(85.0, hum + 1.0)
                        await humidity.write_value(round(new_humidity, 1))
                        
                    # 전원 꺼짐 이벤트
                    if temp != await current_temp.read_value():
                        evgen.event.Message = ua.LocalizedText("AC is off")
                        evgen.event.Severity = 50
                        evgen.event.CurrentTemperature = new_temp
                        evgen.event.TargetTemperature = target
                        evgen.event.PowerState = False
                        await evgen.trigger()
                
            except Exception as e:
                _logger.error("서버 에러: %s", str(e))
            
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())