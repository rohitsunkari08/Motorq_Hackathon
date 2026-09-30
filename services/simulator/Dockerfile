# Build stage
FROM golang:1.23-alpine AS builder

WORKDIR /src

RUN apk add --no-cache git ca-certificates

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-s -w" \
    -o /bin/simulator \
    ./cmd/simulator

# Runtime stage
FROM alpine:3.20

RUN apk --no-cache add ca-certificates tzdata && \
    addgroup -g 10001 appgroup && \
    adduser -u 10001 -G appgroup -D appuser

COPY --from=builder /bin/simulator /usr/local/bin/simulator

USER appuser:appgroup

EXPOSE 2113

ENTRYPOINT ["/usr/local/bin/simulator"]
CMD ["--mode=live", "--rate=100000", "--vehicles=100000"]
