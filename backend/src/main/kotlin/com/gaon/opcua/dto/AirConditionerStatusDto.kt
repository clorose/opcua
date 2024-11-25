package com.gaon.opcua.dto

data class AirConditionerStatusDto(
    val currentTemperature: Double,
    val targetTemperature: Double,
    val humidity: Double,
    val powerUsage: Double,
    val electricityCost: Int,
    val power: Boolean,
    val namespaceIndex: Int
)