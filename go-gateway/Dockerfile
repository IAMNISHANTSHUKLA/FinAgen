FROM golang:1.22-alpine AS builder

WORKDIR /app

RUN apk add --no-cache gcc musl-dev

COPY go.mod go.sum* ./
RUN go mod download 2>/dev/null || true

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /gateway ./cmd/server/

FROM alpine:3.19

RUN apk add --no-cache ca-certificates

COPY --from=builder /gateway /gateway

EXPOSE 8080 8443

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --spider -q http://localhost:8080/health || exit 1

ENTRYPOINT ["/gateway"]
