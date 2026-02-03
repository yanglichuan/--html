package com.example.stock.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {

    @GetMapping("/")
    public String hello() {
        return "<h1>Hello from Tencent Cloud!</h1><p>Spring Boot Application Deployed Successfully.</p>";
    }
}
