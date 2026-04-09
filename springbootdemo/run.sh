#!/bin/bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"

echo "Starting Library Management System..."

# Check Java
if ! command -v java &> /dev/null; then
    echo "Error: Java is not installed or not in PATH."
    echo "Please install Java 17 or later."
    exit 1
fi

# Check Maven
if ! command -v mvn &> /dev/null; then
    echo "Error: Maven is not installed or not in PATH."
    echo "Please install Maven."
    exit 1
fi

echo "Building and running the application..."
mvn spring-boot:run
