package com.gaon.opcua.controller

import com.gaon.opcua.dto.AirConditionerStatusDto
import com.gaon.opcua.dto.TemperatureUpdateDto
import jakarta.annotation.PostConstruct
import jakarta.annotation.PreDestroy
import org.eclipse.milo.opcua.sdk.client.OpcUaClient
import org.eclipse.milo.opcua.sdk.client.api.config.OpcUaClientConfigBuilder
import org.eclipse.milo.opcua.stack.core.types.builtin.*
import org.eclipse.milo.opcua.stack.core.types.enumerated.TimestampsToReturn
import org.slf4j.LoggerFactory
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*
import java.util.Optional
import java.util.concurrent.ConcurrentHashMap

@RestController
@RequestMapping("/api/ac")
class AirConditionerController {
    private val logger = LoggerFactory.getLogger(this::class.java)

    companion object {
        private const val NAMESPACE_URI = "http://gaon.opcua.server"
        private const val ENDPOINT_URL = "opc.tcp://localhost:4840/freeopcua/server/"
    }

    private lateinit var client: OpcUaClient
    private val nodeCache = ConcurrentHashMap<String, NodeId>()

    @PostConstruct
    fun init() {
        connectClient()
    }

    @PreDestroy
    fun cleanup() {
        try {
            client.disconnect()
        } catch (e: Exception) {
            logger.error("Cleanup failed", e)
        }
    }

    private fun connectClient() {
        try {
            client = OpcUaClient.create(
                ENDPOINT_URL,
                { endpoints -> Optional.ofNullable(endpoints.firstOrNull()) },
                { builder: OpcUaClientConfigBuilder ->
                    builder.setApplicationName(LocalizedText("Gaon AC Controller"))
                        .setApplicationUri("urn:gaon:ac:client")
                        .build()
                }
            )
            client.connect().get()
            logger.info("Successfully connected to OPC UA server")
        } catch (e: Exception) {
            logger.error("Failed to connect to OPC UA server", e)
            throw e
        }
    }

    private fun getNodeId(identifier: String): NodeId {
        return nodeCache.computeIfAbsent(identifier) {
            val namespaceIndex = client.namespaceTable.getIndex(NAMESPACE_URI)
            NodeId(namespaceIndex!!, "AirConditioner.$identifier")
        }
    }

    @GetMapping("/status")
    fun getStatus(): ResponseEntity<AirConditionerStatusDto> {
        return try {
            val namespaceIndex = client.namespaceTable.getIndex(NAMESPACE_URI)?.toInt() ?: 0

            val currentTemp = readValue("CurrentTemperature")?.value?.value as? Double
            val targetTemp = readValue("TargetTemperature")?.value?.value as? Double
            val humidity = readValue("Humidity")?.value?.value as? Double
            val powerUsage = readValue("PowerUsage")?.value?.value as? Double
            val electricityCost = readValue("ElectricityCost")?.value?.value as? Int
            val power = readValue("Power")?.value?.value as? Boolean

            val status = AirConditionerStatusDto(
                currentTemperature = currentTemp ?: 0.0,
                targetTemperature = targetTemp ?: 24.0,
                humidity = humidity ?: 0.0,
                powerUsage = powerUsage ?: 0.0,
                electricityCost = electricityCost ?: 0,
                power = power ?: false,
                namespaceIndex = namespaceIndex
            )

            ResponseEntity.ok(status)
        } catch (e: Exception) {
            logger.error("Failed to get AC status", e)
            ResponseEntity.internalServerError().build()
        }
    }

    @PostMapping("/temperature")
    fun setTemperature(@RequestBody request: TemperatureUpdateDto): ResponseEntity<Any> {
        return try {
            if (request.temperature < 18 || request.temperature > 30) {
                return ResponseEntity.badRequest().body(mapOf(
                    "error" to "Temperature must be between 18°C and 30°C"
                ))
            }

            val nodeId = getNodeId("TargetTemperature")
            val value = DataValue(Variant(request.temperature))

            client.writeValue(nodeId, value).get()
            logger.info("Temperature set to: ${request.temperature}°C")

            ResponseEntity.ok(mapOf(
                "success" to true,
                "temperature" to request.temperature
            ))
        } catch (e: Exception) {
            logger.error("Failed to set temperature", e)
            ResponseEntity.internalServerError().body(mapOf(
                "error" to (e.message ?: "Unknown error")
            ))
        }
    }

    @PostMapping("/power")
    fun togglePower(@RequestBody power: Map<String, Boolean>): ResponseEntity<Any> {
        return try {
            val powerState = power["power"] ?: throw IllegalArgumentException("Power state not provided")

            val nodeId = getNodeId("Power")
            val value = DataValue(Variant(powerState))

            client.writeValue(nodeId, value).get()
            logger.info("Power state set to: $powerState")

            ResponseEntity.ok(mapOf(
                "success" to true,
                "power" to powerState
            ))
        } catch (e: Exception) {
            logger.error("Failed to toggle power", e)
            ResponseEntity.internalServerError().body(mapOf(
                "error" to (e.message ?: "Unknown error")
            ))
        }
    }

    private fun readValue(identifier: String): DataValue? {
        return try {
            val nodeId = getNodeId(identifier)
            client.readValue(0.0, TimestampsToReturn.Both, nodeId).get()
        } catch (e: Exception) {
            logger.error("Failed to read value for $identifier", e)
            null
        }
    }
}