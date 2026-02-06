package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

type Response struct {
	Message string `json:"message"`
	Time    string `json:"time"`
	Host    string `json:"host"`
}

func helloHandler(w http.ResponseWriter, r *http.Request) {
	hostname, _ := os.Hostname()
	resp := Response{
		Message: "Hello from Go Service! 🚀",
		Time:    time.Now().Format(time.RFC3339),
		Host:    hostname,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func statusHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Go Service is running smoothly!")
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8095"
	}

	http.HandleFunc("/", helloHandler)
	http.HandleFunc("/status", statusHandler)

	fmt.Printf("Starting server on port %s...\n", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatal(err)
	}
}
