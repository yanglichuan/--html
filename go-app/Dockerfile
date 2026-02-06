# Build stage
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY . .
# Disable CGO for static binary
ENV CGO_ENABLED=0
RUN go build -o main .

# Run stage
FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/main .
EXPOSE 8095
ENV PORT=8095
CMD ["./main"]
