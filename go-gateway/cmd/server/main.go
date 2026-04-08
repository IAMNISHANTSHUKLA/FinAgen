package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/finagentx/go-gateway/application"
	"github.com/finagentx/go-gateway/domain"
	"github.com/finagentx/go-gateway/infrastructure/audit"
	authpkg "github.com/finagentx/go-gateway/infrastructure/auth"
	"github.com/finagentx/go-gateway/infrastructure/resilience"
	"github.com/finagentx/go-gateway/infrastructure/streaming"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"google.golang.org/grpc"
)

func main() {
	// ─── Structured Logging ───
	zerolog.TimeFieldFormat = time.RFC3339Nano
	log.Logger = zerolog.New(os.Stdout).With().
		Timestamp().
		Str("service", "go-gateway").
		Logger()

	log.Info().Msg("FinAgentX Go Gateway starting")

	// ─── Configuration ───
	grpcPort := getEnv("GRPC_PORT", "8080")
	restPort := getEnv("REST_PORT", "8443")
	kafkaServers := getEnv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
	aiCoreURL := getEnv("AI_CORE_URL", "http://localhost:8000")

	// ─── Dependency Injection ───
	detector := application.NewAnomalyDetector()
	auditLogger := audit.NewS3AuditLogger("audit-logs")
	breaker := resilience.NewAICoreBreaker()

	// ─── Kafka Consumer ───
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	consumer := streaming.NewKafkaConsumer(
		kafkaServers, "transactions", "finagentx-gateway",
		10, detector,
	)
	go func() {
		if err := consumer.Start(ctx); err != nil {
			log.Error().Err(err).Msg("Kafka consumer error")
		}
	}()

	// ─── gRPC Server (JWT-secured via unary interceptor) ───
	grpcServer := grpc.NewServer(
		grpc.UnaryInterceptor(authpkg.JWTMiddleware()),
	)

	// ─── REST Server (JWT-secured middleware) ───
	mux := http.NewServeMux()

	// Health endpoints — public, no auth
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{
			"status": "healthy", "service": "go-gateway",
		})
	})
	mux.HandleFunc("/ready", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ready"})
	})

	// Prometheus metrics — public
	mux.Handle("/metrics", promhttp.Handler())

	// ─── Secured API Routes (JWT + Circuit Breaker + Audit) ───

	// POST /api/v1/query — Forward to Python AI Core
	mux.Handle("/api/v1/query", jwtRESTMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, `{"error":"method_not_allowed"}`, http.StatusMethodNotAllowed)
			return
		}

		bodyBytes, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, `{"error":"invalid_body"}`, http.StatusBadRequest)
			return
		}
		defer r.Body.Close()

		var reqBody map[string]interface{}
		if err := json.Unmarshal(bodyBytes, &reqBody); err != nil {
			http.Error(w, `{"error":"invalid_json"}`, http.StatusBadRequest)
			return
		}

		// Audit log the request (WORM, hash-chained)
		sessionID, _ := reqBody["session_id"].(string)
		userID := r.Header.Get("X-User-ID")
		auditLogger.Append(domain.AuditEntry{
			SessionID:  sessionID,
			UserID:     userID,
			Action:     "query_submitted",
			ToolCalled: "ai-core-proxy",
			Input:      string(bodyBytes),
		})

		// Forward with circuit breaker
		var resp *http.Response
		cbErr := breaker.Execute(func() (interface{}, error) {
			proxyReq, _ := http.NewRequestWithContext(
				r.Context(), http.MethodPost,
				aiCoreURL+"/api/v1/query",
				bytes.NewReader(bodyBytes),
			)
			proxyReq.Header.Set("Content-Type", "application/json")
			proxyReq.Header.Set("Authorization", r.Header.Get("Authorization"))
			proxyReq.Header.Set("X-Correlation-ID", r.Header.Get("X-Correlation-ID"))

			client := &http.Client{Timeout: 30 * time.Second}
			var callErr error
			resp, callErr = client.Do(proxyReq)
			return nil, callErr
		})

		if cbErr != nil {
			log.Error().Err(cbErr).Msg("AI Core call failed (circuit breaker)")
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusServiceUnavailable)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":   "ai_core_unavailable",
				"message": "AI Core is temporarily unavailable. Circuit breaker is OPEN.",
				"retry":   true,
			})
			return
		}

		defer resp.Body.Close()
		respBytes, _ := io.ReadAll(resp.Body)

		// Audit log the response
		auditLogger.Append(domain.AuditEntry{
			SessionID:  sessionID,
			UserID:     userID,
			Action:     "query_response",
			ToolCalled: "ai-core-proxy",
			Output:     string(respBytes[:minInt(len(respBytes), 500)]),
		})

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(resp.StatusCode)
		w.Write(respBytes)
	})))

	// GET /api/v1/alerts — Get active anomaly alerts
	mux.Handle("/api/v1/alerts", jwtRESTMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"alerts": []interface{}{},
			"count":  0,
		})
	})))

	// GET /api/v1/trace/:session — Get agent trace
	mux.Handle("/api/v1/trace/", jwtRESTMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		sessionID := strings.TrimPrefix(r.URL.Path, "/api/v1/trace/")
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"session_id": sessionID,
			"steps":      []interface{}{},
		})
	})))

	// POST /api/v1/feedback — Submit feedback (JWT-secured)
	mux.Handle("/api/v1/feedback", jwtRESTMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, `{"error":"method_not_allowed"}`, http.StatusMethodNotAllowed)
			return
		}
		var body map[string]interface{}
		json.NewDecoder(r.Body).Decode(&body)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{
			"status":     "feedback_received",
			"session_id": body["session_id"].(string),
		})
	})))

	// POST /api/v1/audit/verify — Verify hash chain integrity
	mux.Handle("/api/v1/audit/verify", jwtRESTMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			SessionID string `json:"session_id"`
		}
		json.NewDecoder(r.Body).Decode(&body)

		valid, err := auditLogger.Verify(body.SessionID)
		w.Header().Set("Content-Type", "application/json")
		if err != nil {
			json.NewEncoder(w).Encode(map[string]interface{}{
				"valid": false, "error": err.Error(),
			})
			return
		}
		json.NewEncoder(w).Encode(map[string]interface{}{
			"valid":      valid,
			"session_id": body.SessionID,
		})
	})))

	// ─── Start gRPC Server ───
	go func() {
		lis, err := net.Listen("tcp", ":"+grpcPort)
		if err != nil {
			log.Fatal().Err(err).Msg("Failed to listen for gRPC")
		}
		log.Info().Str("port", grpcPort).Msg("gRPC server listening")
		if err := grpcServer.Serve(lis); err != nil {
			log.Fatal().Err(err).Msg("gRPC server error")
		}
	}()

	// ─── Start REST Server ───
	restServer := &http.Server{
		Addr:         ":" + restPort,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		log.Info().Str("port", restPort).Msg("REST server listening")
		if err := restServer.ListenAndServe(); err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("REST server error")
		}
	}()

	// ─── Graceful Shutdown ───
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	sig := <-sigChan

	log.Info().Str("signal", sig.String()).Msg("Shutdown signal received")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer shutdownCancel()

	grpcServer.GracefulStop()
	restServer.Shutdown(shutdownCtx)
	consumer.Stop()
	cancel()

	log.Info().Msg("FinAgentX Go Gateway stopped")
}

// ─── JWT REST Middleware ───
// Wraps http.Handler to validate JWT on all /api/* routes.
func jwtRESTMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		publicKey := os.Getenv("JWT_PUBLIC_KEY")
		if publicKey == "" {
			// Dev mode: skip auth
			next.ServeHTTP(w, r)
			return
		}

		authHeader := r.Header.Get("Authorization")
		if authHeader == "" || !strings.HasPrefix(authHeader, "Bearer ") {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			json.NewEncoder(w).Encode(map[string]string{
				"error": "missing_or_invalid_authorization_header",
			})
			return
		}

		token := strings.TrimPrefix(authHeader, "Bearer ")
		claims, err := authpkg.ValidateToken(token, publicKey)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			json.NewEncoder(w).Encode(map[string]string{
				"error": "invalid_token", "detail": err.Error(),
			})
			return
		}

		// Inject user info into request headers for downstream
		r.Header.Set("X-User-ID", claims.Subject)
		r.Header.Set("X-User-Roles", strings.Join(claims.Roles, ","))

		next.ServeHTTP(w, r)
	})
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}
