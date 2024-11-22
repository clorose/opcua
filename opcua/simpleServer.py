# path: opcua/simpleServer.py
# description: OPC UA 서버를 구현하는 간단한 예제 코드

import asyncio
import logging
from asyncua import Server, ua

_logger = logging.getLogger(__name__)

class VariableHandler:
    async def datachange_notification(self, node, val, data):
        _logger.info("Counter value changed to: %s", val)

async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")

    # namespace 설정
    uri = "http://examples.freeopcua.github.io"
    idx = await server.register_namespace(uri)

    # counter 객체/변수 생성
    myobj = await server.nodes.objects.add_object(idx, "MyObject")
    counter = await myobj.add_variable(idx, "Counter", 0)
    await counter.set_writable()
    
    # 값 변경 모니터링을 위한 subscription 생성
    handler = VariableHandler()
    subscription = await server.create_subscription(500, handler)
    await subscription.subscribe_data_change([counter])
    
    _logger.info("Server started at opc.tcp://0.0.0.0:4840")
    
    async with server:
        while True:
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    # uaprocessor의 읽기/쓰기 요청은 숨기고 값 변경 로그만 표시
    logging.getLogger("asyncua").setLevel(logging.WARNING)
    
    asyncio.run(main())