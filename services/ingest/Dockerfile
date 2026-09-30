# Build stage
FROM golang:alpine AS builder

WORKDIR /src

RUN apk add --no-cache git ca-certificates

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-s -w" \
    -o /bin/ingest \
    ./cmd/ingest

# Runtime stage
FROM alpine:3.20

RUN apk --no-cache add ca-certificates tzdata && \
    addgroup -g 10001 appgroup && \
    adduser -u 10001 -G appgroup -D appuser

COPY --from=builder /bin/ingest /usr/local/bin/ingest

USER appuser:appgroup

EXPOSE 2112

ENTRYPOINT ["/usr/local/bin/ingest"]
CMD ["--mode=normalize"]
