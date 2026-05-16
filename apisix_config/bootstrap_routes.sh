# creates all routes and upstream using the Admin api. used becuase apisix use etcd to store routes and dynamic routing helps in manipulating service without restarting the gate way

# port used by admin
ADMIN_URL = "http://apisix:9180"
ADMIN_KEY = "edd1c9f034335f136f87ad84b625c8f1" # used from config.yaml

# waits for the api to be ready for usage
echo ""
echo "=== Waiting for APISIX Admin API ==="
until curl -sf -o /dev/null -H "X-API-KEY: ${ADMIN_KEY}" "${ADMIN_URL}/apisix/admin/routes"; do
  echo "  not ready, retrying in 3s..."
  sleep 3

done
echo "APISIX is ready"

# create upstreams

# for auth service
log "Creating upstream: auth-service"
curl -sf -X PUT "$ADMIN_URL/apisix/admin/upstreams/1" \
    -H "X-API-KEY: $ADMIN_KEY" \
    -H "Content-Type: application/json"\
    -d '{
        "id":1,
        "name": "auth-service",
        "desc": "FastAPI authentication microservice(port 8001)",
        "type": "roundrobin",
        "nodes":{
            "auth-service:8001":1
        },
        "scheme":"http",
        "pass_host": "pass",
        "keepalive_pool": {
            "size" :320,
            "idle_timeout": 60,
            "requests":1000
        },   
        "checks":{
            "active":{
            "type":"http",
            "http_path":"/health",
            "healthy": {
                "interval":10,
                "successes":2
            },
            "unhealthy":{
                "interval":5,
                "http_failures":3
            }
        }
    }'
echo " ✓ auth-service upstream created"

# create routes

# ROUTE 1001: POST/auth/register
log "Creating route: POST /auth/register"
curl -sf -X PUT "$ADMIN_URL/apisix/admin/routes/1001" \
    -H "X-API-KEY: $ADMIN_KEY" \
    -H "Content-Type: application/json"\
    -d '{
        "id":1001,
        "name":"auth-register",
        "desc": "User registration - public endpoint, no auth required",
        "uri":"/auth/register",
        "methods": ["POST"],
        "upstream_id": 1,
        "plugins":{
            "proxy-rewrite":{
                "uri": "/register
            },
            "request-id":{
                "header_name":"X-Request-Id",
                "include_in_response": true
            },
            "limit-count":{
                "count": 20,
                "time-window": 60,
                "key-type" : "remote_addr",
                "rejected_code": 429,
                "rejected_msg":"Too many registration attempts. Please wait." 
            },
            "cors" :{
                "allow_origins": "*",
                "allow_methods":"POST",
                "allow_headers" : "Content-Type, Authorization",
                "expose_headers":"X-Request-Id",
                "max_age":3600    
            }
        }
    }'
echo " ✓ Route 1001: POST /auth/register"

# ROUTE 1002: POST/auth/login 
log "Creating route: POST /auth/login"
curl -sf -X PUT "$ADMIN_URL/apisix/admin/routes/1002" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "id": 1002,
        "name": "auth-login",
        "desc": "User login — public endpoint, rate-limited to prevent brute force",
        "uri": "/auth/login",
        "methods": ["POST"],
        "upstream_id": 1,
        "plugins": {
            "proxy-rewrite": {
                "uri": "/login"
            },
            "request-id": {
                "header_name": "X-Request-Id",
                "include_in_response": true
            },
            "limit-count": {
                "count": 10,
                "time_window": 60,
                "key_type": "remote_addr",
                "rejected_code": 429,
                "rejected_msg": "Too many login attempts. Please wait 60 seconds."
            },
            "cors": {
                "allow_origins": "*",
                "allow_methods": "POST",
                "allow_headers": "Content-Type,Authorization",
                "expose_headers": "X-Request-Id",
                "max_age": 3600
            }
        }
    }'
echo " ✓ Route 1002: POST /auth/login"

# ROUTE 1003: POST/auth/refresh
log "Creating route: POST /auth/refresh"
curl -sf -X PUT "$ADMIN_URL/apisix/admin/routes/1003" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "id": 1003,
        "name": "auth-refresh",
        "desc": "Token refresh — public, the refresh token itself is the credential",
        "uri": "/auth/refresh",
        "methods": ["POST"],
        "upstream_id": 1,
        "plugins": {
            "proxy-rewrite": {
                "uri": "/refresh"
            },
            "request-id": {
                "header_name": "X-Request-Id",
                "include_in_response": true
            },
            "limit-count": {
                "count": 30,
                "time_window": 60,
                "key_type": "remote_addr",
                "rejected_code": 429,
                "rejected_msg": "Rate limit exceeded."
            }
        }
    }'


# ROUTE 1004: GET/auth/health
log "Creating route: GET/auth/health"
curl -sf -X PUT "$ADMIN_URL/apisix/admin/routes/1003" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "id": 1004,
        "name":"auth-health",
        "desc":"Auth service health check",
        "uri" : "/auth/health",
        "methods":["GET"],
        "upstream_id":1,
        "plugins": {
            "proxy-rewrite" : {
                "uri":"/health"
            }
        }
    }'

echo " ✓ Route 1004: GET /auth/health"


# ROUTE 9001: gateway leve health check
log "Creating route: GET /health (gateway-level)"
curl -sf -X PUT "$ADMIN_URL/apisix/admin/routes/9001" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "id": 9001,
        "name": "gateway-health",
        "desc": "APISIX gateway health check — answered by APISIX directly, no upstream needed",
        "uri": "/health",
        "methods": ["GET"],
        "plugins": {
        "echo": {
                "body": "{\"status\":\"ok\",\"service\":\"apisix-gateway\"}",
                "headers": {
                "Content-Type": "application/json"
                }
            }
        }
    }'
echo " ✓ Route 9001: GET /health (gateway)"
 