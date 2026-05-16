# Add a brand new microservice to APISIX at runtime
# when we build a new microservice this script needs to excute without restarting anything

ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
ADMIN_KEY="${APISIX_ADMIN_KEY:-edd1c9f034335f136f87ad84b625c8f1}"

UPSTREAM_ID = "$1"
SERVICE_NAME = "$2"
HOST_PORT = "$3"
PATH_PREFIX = "$4"
STRIP_PREFIX = "$5"

if [-z "$UPSTREAM_ID"] || [-z "$SERVICE_NAME"] || [-z "$HOST_PORT"] || [-z "$PATH_PREFIX"]; then
    echo "Usage: $0 <upstream_id> <service_name> <host:port> <path_prefix> [strip_prefix]"
    echo "Example: $0 2 org-service org-service:8002 '/org/*' '/org'"
    exit 1
fi

echo ""
echo "=== Registering service: $SERVICE_NAME ==="
echo "    Upstream ID : $UPSTREAM_ID"
echo "    Backend     : $HOST_PORT"
echo "    Route path  : $PATH_PREFIX"

# update upstream:

echo ""
echo "--> Updating upstream $UPSTREAM_ID → $HOST_PORT"
curl -sf -X PATCH "$ADMIN_URL/apisix/admin/upstreams/$UPSTREAM_ID" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"nodes\": {
      \"$HOST_PORT\": 1
    },
    \"checks\": {
      \"active\": {
        \"type\": \"http\",
        \"http_path\": \"/health\",
        \"healthy\": { \"interval\": 10, \"successes\": 2 },
        \"unhealthy\": { \"interval\": 5, \"http_failures\": 3 }
      }
    }
  }"
echo " ✓ Upstream updated"
 
#  catch all-routes
# Route ID convention: upstream_id * 1000 + 1  (e.g. upstream 2 → route 2001)
ROUTE_ID=$(( UPSTREAM_ID * 1000 + 1 ))
 
REWRITE_REGEX="^${STRIP_PREFIX:-$PATH_PREFIX}/(.*)"
# Remove trailing /* from strip_prefix for the regex replacement
CLEAN_STRIP=$(echo "$STRIP_PREFIX" | sed 's|/\*||g')
 
echo "Creating route $ROUTE_ID for $PATH_PREFIX"
curl -sf -X PUT "$ADMIN_URL/apisix/admin/routes/$ROUTE_ID" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": $ROUTE_ID,
    \"name\": \"$SERVICE_NAME-catch-all\",
    \"desc\": \"Catch-all route for $SERVICE_NAME — auto-registered by add_service.sh\",
    \"uri\": \"$PATH_PREFIX\",
    \"upstream_id\": $UPSTREAM_ID,
    \"plugins\": {
      \"proxy-rewrite\": {
        \"regex_uri\": [\"^$CLEAN_STRIP/(.*)\", \"/\$1\"]
      },
      \"request-id\": {
        \"header_name\": \"X-Request-Id\",
        \"include_in_response\": true
      },
      \"cors\": {
        \"allow_origins\": \"*\",
        \"allow_methods\": \"GET,POST,PUT,DELETE,PATCH,OPTIONS\",
        \"allow_headers\": \"Content-Type,Authorization,X-Request-Id\",
        \"expose_headers\": \"X-Request-Id\"
      }
    }
  }"
echo " ✓ Route $ROUTE_ID created"
 
echo ""
echo "=== $SERVICE_NAME is now live! ==="
echo "    Call: http://localhost:9080$CLEAN_STRIP/<any-path>"
echo "    Backend receives: /<any-path>"