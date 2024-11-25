# OPC UA 통신 구조

OPC UA 서버를 통해 에어컨 하드웨어와 직접 통신하는 시스템을 구현합니다.

## 1. NodeId 시스템 구현

```python
# 계층적 구조의 NodeId 설정
objects = server.nodes.objects
ac_system = await objects.add_object(
    ua.NodeId("AirConditioner", idx),      # 최상위 객체
    ua.QualifiedName("AirConditioner", idx)
)

# 하위 변수 노드들 생성
power = await ac_system.add_variable(
    ua.NodeId("AirConditioner.Power", idx),  # 계층 구조를 반영한 NodeId
    ua.QualifiedName("Power", idx),
    False
)
await power.set_writable()

temperature = await ac_system.add_variable(
    ua.NodeId("AirConditioner.Temperature", idx),
    ua.QualifiedName("Temperature", idx),
    24.0
)
await temperature.set_writable()
```

* **계층적 NodeId 설정**: `AirConditioner.Power`, `AirConditioner.Temperature` 등 계층 구조를 반영한 NodeId를 사용하여 명확한 네임스페이스를 구성합니다.
* **변수 노드 생성 및 설정**: `power`와 `temperature` 변수 노드를 생성하고, 쓰기 가능하도록 설정하여 외부에서 제어할 수 있게 합니다.
* **최상위 객체 등록**: `ac_system` 객체를 OPC UA 서버의 최상위 객체로 등록하여 에어컨 시스템의 루트로 사용합니다.

## 2. 구독 시스템 구현

```python
class SubscriptionHandler:
    async def datachange_notification(self, node, val, data):
        try:
            name = (await node.read_browse_name()).Name
            _logger.info("DataChange: %s = %s", name, val)
        except Exception as e:
            _logger.error("Error: %s", e)

# 500ms 주기로 데이터 변경 감지
handler = SubscriptionHandler()
subscription = await server.create_subscription(500, handler)
await subscription.subscribe_data_change([power, temperature])
```

* **SubscriptionHandler 클래스**: 데이터 변경 시 호출되는 콜백 함수를 포함하여 데이터 변경 사항을 처리합니다.
* **데이터 변경 감지 주기 설정**: 500ms 주기로 `power`와 `temperature` 노드의 변경 사항을 구독하여 실시간 모니터링을 구현합니다.
* **예외 처리 및 로깅**: 데이터 변경 처리 중 발생하는 예외를 처리하고, 변경 사항을 로깅하여 시스템의 안정성을 높입니다.

## 3. 통신 루프 구현

```python
async with server:
    while True:
        try:
            # NodeId를 통한 데이터 접근
            is_power_on = await power.read_value()
            current_temp = await temperature.read_value()
            
            if changed:
                await handle_state_change(is_power_on, current_temp)
                
        except Exception as e:
            _logger.error("Error: %s", str(e))
        
        await asyncio.sleep(1)
```

* **비동기 통신 루프**: `asyncio`를 활용하여 서버와의 비동기 통신 루프를 구성합니다.
* **데이터 읽기 및 상태 변경 처리**: `power`와 `temperature`의 현재 값을 읽어와 상태 변경이 있으면 `handle_state_change` 함수를 호출합니다.
* **예외 처리 및 로깅**: 통신 중 발생하는 예외를 처리하고 에러를 로깅하여 시스템의 신뢰성을 유지합니다.

## 주요 특징

### NodeId 시스템

- **계층적 구조 설계**: NodeId를 계층적으로 설계하여 에어컨 시스템의 각 구성 요소에 대한 명확한 식별자를 제공합니다.
- **클라이언트 접근성 향상**: 모든 클라이언트가 동일한 NodeId를 사용하여 일관된 방식으로 서버에 접근할 수 있습니다.
- **다양한 클라이언트 지원**: Python, Kotlin 등 다양한 언어의 클라이언트에서 동일한 NodeId를 사용하여 서버와 통신합니다.

### 구독 기반 통신

- **실시간 데이터 동기화**: 구독 시스템을 통해 500ms 주기로 데이터 변경 사항을 감지하여 실시간 동기화를 구현합니다.
- **효율적인 리소스 사용**: 관심 있는 노드만 구독하여 네트워크 및 시스템 리소스를 효율적으로 사용합니다.
- **확장성**: 구독 노드를 쉽게 추가하거나 제거할 수 있어 시스템 확장에 용이합니다.

---

# OPC UA Bridge 구현

OPC UA 서버와 RESTful API 간의 프로토콜 브릿지를 구현하여 에어컨 제어 기능을 제공합니다.

## 1. 프로토콜 브릿지 설정

```kotlin
class AirConditionerController {
    companion object {
        private const val NAMESPACE_URI = "http://gaon.opcua.server"
        private const val ENDPOINT_URL = "opc.tcp://localhost:4840/freeopcua/server/"
    }

    private lateinit var client: OpcUaClient
    private val nodeCache = ConcurrentHashMap<String, NodeId>()
}
```

* **네임스페이스 및 엔드포인트 설정**: `NAMESPACE_URI`와 `ENDPOINT_URL`을 정의하여 OPC UA 서버의 네임스페이스와 엔드포인트를 설정합니다.
* **OPC UA 클라이언트 초기화**: `OpcUaClient` 인스턴스를 선언하여 OPC UA 서버와의 통신을 준비합니다.
* **NodeId 캐싱**: `nodeCache`를 사용하여 `NodeId`를 캐싱함으로써 성능을 향상시킵니다.

## 2. OPC UA ↔ REST 변환 계층

```kotlin
// REST -> OPC UA (쓰기 작업)
@PostMapping("/power")
fun togglePower(@RequestBody power: Map<String, Boolean>): ResponseEntity<Any> {
    val powerState = power["power"] ?: throw IllegalArgumentException("Power state not provided")
    val nodeId = getNodeId("Power")
    val value = DataValue(Variant(powerState))
    client.writeValue(nodeId, value).get()
    return ResponseEntity.ok(mapOf("success" to true, "power" to powerState))
}

// OPC UA -> REST (읽기 작업)
@GetMapping("/status")
fun getStatus(): ResponseEntity<AirConditionerStatusDto> {
    val currentTemp = readValue("CurrentTemperature")?.value?.value as? Double
    val targetTemp = readValue("TargetTemperature")?.value?.value as? Double
    val power = readValue("Power")?.value?.value as? Boolean
    
    return ResponseEntity.ok(AirConditionerStatusDto(
        currentTemperature = currentTemp ?: 0.0,
        targetTemperature = targetTemp ?: 24.0,
        power = power ?: false
    ))
}
```

* **전원 제어 API**: `/power` 엔드포인트를 통해 RESTful API로 전원 상태를 토글할 수 있습니다.
  * 요청 바디에서 `power` 상태를 받아와 OPC UA 서버의 해당 노드에 값을 씁니다.
* **상태 조회 API**: `/status` 엔드포인트를 통해 현재 에어컨 상태를 조회할 수 있습니다.
  * OPC UA 서버에서 필요한 값을 읽어와 DTO 형태로 응답합니다.
* **에러 처리**: 요청된 데이터가 없을 경우 `IllegalArgumentException`을 발생시켜 오류를 처리합니다.

## 3. 프로토콜 변환 유틸리티

```kotlin
// OPC UA 통신용 NodeId 관리
private fun getNodeId(identifier: String): NodeId {
    return nodeCache.computeIfAbsent(identifier) {
        val namespaceIndex = client.namespaceTable.getIndex(NAMESPACE_URI)
        NodeId(namespaceIndex!!, "AirConditioner.$identifier")
    }
}

// OPC UA 데이터 읽기 작업 추상화
private fun readValue(identifier: String): DataValue? {
    return try {
        val nodeId = getNodeId(identifier)
        client.readValue(0.0, TimestampsToReturn.Both, nodeId).get()
    } catch (e: Exception) {
        logger.error("Failed to read value for $identifier", e)
        null
    }
}
```

* **NodeId 관리**: `getNodeId` 함수는 주어진 식별자에 대한 `NodeId`를 반환하며, 캐시를 활용하여 성능을 향상시킵니다.
* **데이터 읽기 추상화**: `readValue` 함수는 특정 노드의 값을 읽어오는 작업을 추상화하여 코드의 재사용성을 높입니다.
* **예외 처리 및 로깅**: 예외 발생 시 에러를 로깅하고 `null`을 반환하여 안정적인 동작을 유지합니다.

## 주요 특징

### 프로토콜 브릿징

- **HTTP/REST ↔ OPC UA 변환**: RESTful API 요청을 OPC UA 통신으로 변환하여 에어컨 제어를 가능하게 합니다.
- **데이터 타입 변환**: DTO와 OPC UA의 `DataValue` 간의 변환을 처리하여 데이터 일관성을 유지합니다.
- **에러 코드 매핑**: OPC UA에서 발생하는 에러를 HTTP 상태 코드로 매핑하여 클라이언트에게 명확한 오류 정보를 제공합니다.

### 성능 최적화

- **NodeId 캐싱**: `NodeId`를 캐싱하여 반복적인 네임스페이스 조회를 줄이고 성능을 향상시킵니다.
- **연결 재사용**: OPC UA 클라이언트의 연결을 유지하고 재사용하여 연결 설정에 따른 오버헤드를 최소화합니다.
- **비동기 처리**: 비동기 작업을 효율적으로 처리하여 서버의 응답 시간을 단축하고 자원을 효율적으로 사용합니다.

### 오류 처리 및 복구

- **자동 재연결**: 연결 실패 시 자동으로 재연결하여 서비스의 가용성을 높입니다.
- **에러 변환**: 프로토콜별로 적절한 에러 변환을 수행하여 오류 상황에서도 시스템의 일관성을 유지합니다.
- **상세 로깅**: 상세한 로그를 남겨 디버깅과 모니터링을 용이하게 합니다.

---

# Next.js 클라이언트 핵심 구현

Next.js를 사용하여 에어컨 제어 UI를 구현하고, 브릿지 서버와 통신하여 상태 관리 및 제어 기능을 제공합니다.

## 1. 상태 관리 및 통신

```typescript
interface ACStatus {
  currentTemperature: number;
  targetTemperature: number;
  humidity: number;
  powerUsage: number;
  electricityCost: number;
  power: boolean;
}

const ACControlPanel = () => {
  const [status, setStatus] = useState<ACStatus | null>(null);
  const [targetTemp, setTargetTemp] = useState(24);

  // 실시간 상태 갱신 (1초마다 서버에서 최신 상태 받아옴)
  useEffect(() => {
    const fetchStatus = async () => {
      const { data } = await axios.get<ACStatus>("/api/ac/status");
      setStatus(data);
    };
    const interval = setInterval(fetchStatus, 1000);
    return () => clearInterval(interval);
  }, []);
}
```

* **상태 인터페이스 정의**: `ACStatus` 인터페이스를 통해 에어컨의 상태를 타입으로 관리합니다.
* **상태 변수 초기화**: `useState`를 사용하여 현재 상태(`status`)와 목표 온도(`targetTemp`)를 관리합니다.
* **실시간 상태 갱신**: `useEffect`를 활용하여 1초마다 서버에서 최신 상태를 받아와 상태를 업데이트합니다.
* **비동기 통신**: `axios`를 사용하여 비동기적으로 API를 호출합니다.

## 2. API Routes (브릿지 서버와의 통신 처리)

```typescript
// 상태 조회 API
export async function GET() {
  const { data } = await axios.get(API_BASE_URL + '/status')
  return NextResponse.json(data)
}

// 온도 제어 API
export async function POST(request: Request) {
  const { temperature } = await request.json()
  if (temperature < 18 || temperature > 30) {
    return NextResponse.json({ error: 'Invalid range' }, { status: 400 })
  }
  const { data } = await axios.post(API_BASE_URL + '/temperature', { temperature })
  return NextResponse.json(data)
}
```

* **상태 조회 엔드포인트**: `GET` 메서드를 통해 클라이언트에서 에어컨의 현재 상태를 조회할 수 있습니다.
  * 브릿지 서버의 `/status` 엔드포인트를 호출하여 데이터를 가져옵니다.
* **온도 설정 엔드포인트**: `POST` 메서드를 통해 목표 온도를 설정할 수 있습니다.
  * 요청된 온도가 유효한 범위(18-30℃)인지 검증합니다.
  * 브릿지 서버의 `/temperature` 엔드포인트로 데이터를 전달합니다.
* **에러 처리**: 유효하지 않은 입력에 대해 적절한 HTTP 상태 코드와 에러 메시지를 반환합니다.

## 3. 제어 로직 (사용자 액션 처리)

```typescript
const ACControlPanel = () => {
  // 전원 ON/OFF 제어
  const handlePowerToggle = async () => {
    await axios.post("/api/ac/power", { power: !status?.power });
  };

  // 설정 온도 변경
  const handleTemperatureChange = async () => {
    if (targetTemp >= 18 && targetTemp <= 30) {
      await axios.post("/api/ac/temperature", { temperature: targetTemp });
    }
  };
```

* **전원 토글 기능**: `handlePowerToggle` 함수는 전원 상태를 토글하는 역할을 합니다.
  * 현재 상태의 `power` 값을 반전시켜 API에 전달합니다.
* **온도 변경 기능**: `handleTemperatureChange` 함수는 목표 온도를 변경합니다.
  * 입력된 온도가 유효한 범위인지 확인한 후 API에 요청을 보냅니다.
* **사용자 인터랙션 처리**: 사용자 액션에 따라 적절한 API를 호출하여 상태를 변경합니다.

## 주요 특징

### 데이터 흐름

- **클라이언트-서버 통신**: UI 컴포넌트에서 API Routes를 통해 브릿지 서버와 통신합니다.
- **실시간 상태 업데이트**: `useEffect`를 활용한 주기적인 상태 갱신으로 최신 정보를 표시합니다.
- **즉각적인 피드백**: 제어 명령 후 즉시 상태를 갱신하여 사용자에게 빠른 피드백을 제공합니다.

### 데이터 유효성 검증

- **클라이언트 측 검증**: 입력된 데이터의 유효성을 검증하여 오류를 사전에 방지합니다.
- **서버 측 추가 검증**: API Routes에서도 유효성 검사를 수행하여 데이터의 무결성을 유지합니다.
- **다단계 검증**: 클라이언트와 서버에서 모두 검증을 수행하여 시스템의 안정성을 향상시킵니다.

### 에러 처리

- **예외 처리 구현**: API 요청 실패 시 예외 처리를 통해 사용자에게 에러 메시지를 제공합니다.
- **안정성 향상**: 네트워크 오류나 서버 오류에 대한 복구 메커니즘을 구현하여 안정적인 사용자 경험을 제공합니다.
- **로깅 및 디버깅 지원**: 로깅을 통해 문제 발생 시 빠르게 대응할 수 있도록 지원합니다.