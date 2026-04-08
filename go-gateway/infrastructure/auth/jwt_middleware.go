package auth

import (
	"context"
	"crypto/rsa"
	"os"
	"strings"

	"github.com/golang-jwt/jwt/v5"
	"github.com/rs/zerolog/log"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

// Claims defines the JWT claims structure for FinAgentX.
type Claims struct {
	jwt.RegisteredClaims
	Roles          []string `json:"roles"`
	AllowedTickers []string `json:"allowed_tickers"`
	MaxRiskLevel   string   `json:"max_risk_level"`
}

// JWTMiddleware creates a gRPC unary server interceptor for RS256 JWT auth.
func JWTMiddleware() grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req interface{},
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (interface{}, error) {
		// Skip auth for health endpoints
		if strings.Contains(info.FullMethod, "Health") {
			return handler(ctx, req)
		}

		publicKeyPEM := os.Getenv("JWT_PUBLIC_KEY")
		if publicKeyPEM == "" {
			// Dev mode — skip auth
			log.Warn().Msg("JWT auth disabled — JWT_PUBLIC_KEY not set")
			return handler(ctx, req)
		}

		// Extract token from metadata
		md, ok := metadata.FromIncomingContext(ctx)
		if !ok {
			return nil, status.Error(codes.Unauthenticated, "missing metadata")
		}

		tokens := md.Get("authorization")
		if len(tokens) == 0 {
			return nil, status.Error(codes.Unauthenticated, "missing authorization token")
		}

		tokenStr := strings.TrimPrefix(tokens[0], "Bearer ")

		// Parse public key
		publicKey, err := jwt.ParseRSAPublicKeyFromPEM([]byte(publicKeyPEM))
		if err != nil {
			log.Error().Err(err).Msg("Failed to parse JWT public key")
			return nil, status.Error(codes.Internal, "auth configuration error")
		}

		// Validate token
		claims := &Claims{}
		token, err := jwt.ParseWithClaims(tokenStr, claims, func(t *jwt.Token) (interface{}, error) {
			if _, ok := t.Method.(*jwt.SigningMethodRSA); !ok {
				return nil, status.Error(codes.Unauthenticated, "unexpected signing method")
			}
			return publicKey, nil
		})

		if err != nil || !token.Valid {
			return nil, status.Error(codes.Unauthenticated, "invalid token")
		}

		// Inject claims into context
		ctx = context.WithValue(ctx, "user_claims", claims)

		log.Info().
			Str("user", claims.Subject).
			Strs("roles", claims.Roles).
			Msg("JWT authenticated")

		return handler(ctx, req)
	}
}

// GetClaimsFromContext extracts JWT claims from gRPC context.
func GetClaimsFromContext(ctx context.Context) *Claims {
	claims, ok := ctx.Value("user_claims").(*Claims)
	if !ok {
		return &Claims{
			Roles: []string{"anonymous"},
		}
	}
	return claims
}

// PublicKeyFromEnv loads the RSA public key from environment.
func PublicKeyFromEnv() *rsa.PublicKey {
	pem := os.Getenv("JWT_PUBLIC_KEY")
	if pem == "" {
		return nil
	}
	key, err := jwt.ParseRSAPublicKeyFromPEM([]byte(pem))
	if err != nil {
		log.Error().Err(err).Msg("Failed to parse RSA public key")
		return nil
	}
	return key
}

// ValidateToken validates a JWT token string against the provided PEM public key.
// Used by the REST middleware (main.go) for HTTP route auth.
func ValidateToken(tokenStr string, publicKeyPEM string) (*Claims, error) {
	publicKey, err := jwt.ParseRSAPublicKeyFromPEM([]byte(publicKeyPEM))
	if err != nil {
		return nil, err
	}

	claims := &Claims{}
	token, err := jwt.ParseWithClaims(tokenStr, claims, func(t *jwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*jwt.SigningMethodRSA); !ok {
			return nil, jwt.ErrSignatureInvalid
		}
		return publicKey, nil
	})

	if err != nil || !token.Valid {
		return nil, err
	}

	return claims, nil
}
