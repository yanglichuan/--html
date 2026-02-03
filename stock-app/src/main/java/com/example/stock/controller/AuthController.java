package com.example.stock.controller;

import com.example.stock.dto.AuthRequest;
import com.example.stock.dto.AuthResponse;
import com.example.stock.model.User;
import com.example.stock.repository.UserRepository;
import com.example.stock.util.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/auth")
public class AuthController {

    @Autowired
    private UserRepository repository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private AuthenticationManager authenticationManager;

    @GetMapping("/welcome")
    public String welcome() {
        return "Welcome this endpoint is not secure";
    }

    @PostMapping("/register")
    public String addNewUser(@RequestBody User user) {
        user.setPassword(passwordEncoder.encode(user.getPassword()));
        repository.save(user);
        return "User Added Successfully";
    }

    @PostMapping("/login")
    public AuthResponse login(@RequestBody AuthRequest authRequest) {
        Authentication authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(authRequest.getUsername(), authRequest.getPassword())
        );
        if (authentication.isAuthenticated()) {
            return new AuthResponse(jwtUtil.generateToken(authRequest.getUsername()));
        } else {
            throw new RuntimeException("invalid user request !");
        }
    }
    
    @GetMapping("/user/profile")
    public String userProfile() {
        return "Welcome to User Profile (Secured Endpoint)";
    }
}
