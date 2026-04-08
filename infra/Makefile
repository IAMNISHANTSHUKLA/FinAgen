# FinAgentX — Build Automation
# Proto codegen, data seeding, linting

PROTO_DIR = proto/v1
GO_OUT = ../go-gateway/proto/v1
PY_OUT = ../python-ai-core/infrastructure/proto

.PHONY: proto-gen seed lint clean help

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

proto-gen: ## Generate protobuf code for Go and Python
	@echo "Generating protobuf code..."
	@mkdir -p $(GO_OUT) $(PY_OUT)
	protoc --proto_path=$(PROTO_DIR) \
		--go_out=$(GO_OUT) --go_opt=paths=source_relative \
		--go-grpc_out=$(GO_OUT) --go-grpc_opt=paths=source_relative \
		--python_out=$(PY_OUT) \
		--grpc-gateway_out=$(GO_OUT) --grpc-gateway_opt=paths=source_relative \
		$(PROTO_DIR)/agent.proto
	@echo "Proto generation complete."

seed: ## Seed market data using yfinance
	@echo "Seeding market data..."
	cd data && python market_data_loader.py
	@echo "Data seeding complete."

lint-python: ## Lint Python AI Core
	cd ../python-ai-core && python -m ruff check . && python -m mypy .

lint-go: ## Lint Go Gateway
	cd ../go-gateway && golangci-lint run ./...

lint-ts: ## Lint TypeScript Dashboard
	cd ../ts-dashboard && npm run lint

lint: lint-python lint-go lint-ts ## Lint all services

test-python: ## Run Python tests
	cd ../python-ai-core && pytest tests/ -v --cov=. --cov-report=term-missing

test-go: ## Run Go tests
	cd ../go-gateway && go test ./... -v -race -cover

test-ts: ## Run TypeScript build check
	cd ../ts-dashboard && npm run build

test: test-python test-go test-ts ## Run all tests

up: ## Start all services via docker-compose
	docker-compose up -d

down: ## Stop all services
	docker-compose down -v

logs: ## Tail all service logs
	docker-compose logs -f

clean: ## Clean generated files
	rm -rf $(GO_OUT)/*.go $(PY_OUT)/*.py
	@echo "Cleaned generated files."
