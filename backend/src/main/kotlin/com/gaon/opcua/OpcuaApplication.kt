package com.gaon.opcua

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class OpcuaApplication

fun main(args: Array<String>) {
	runApplication<OpcuaApplication>(*args)
}
