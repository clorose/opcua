// src/main/kotlin/com/gaon/opcua/config/SwaggerConfig.kt
package com.gaon.opcua.config

import io.swagger.v3.oas.models.OpenAPI
import io.swagger.v3.oas.models.info.Info
import io.swagger.v3.oas.models.servers.Server
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

@Configuration
class SwaggerConfig {
    @Bean
    fun openAPI(): OpenAPI = OpenAPI()
        .info(
            Info()
                .title("Air Conditioner Control API")
                .description("OPC UA를 통한 에어컨 제어 API")
                .version("v1.0")
        )
        .addServersItem(
            Server()
                .url("/")
                .description("Default Server URL")
        )
}