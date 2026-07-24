
BASE="http://localhost:8000"

echo "== GET / =="
curl -s "$BASE/" ; echo -e "\n"

echo "== GET /health =="
curl -s "$BASE/health" ; echo -e "\n"

echo "== GET /api/v1/groundwater/states =="
curl -s "$BASE/api/v1/groundwater/states" ; echo -e "\n"

echo "== GET /api/v1/groundwater/status/Punjab =="
curl -s "$BASE/api/v1/groundwater/status/Punjab" ; echo -e "\n"

echo "== GET /api/v1/groundwater/forecast/Punjab?district=Sangrur =="
curl -s "$BASE/api/v1/groundwater/forecast/Punjab?district=Sangrur" ; echo -e "\n"

echo "== POST /api/v1/chat (status question) =="
curl -s -X POST "$BASE/api/v1/chat" -H "Content-Type: application/json" \
  -d '{"message": "What is the groundwater status in Wardha?"}' ; echo -e "\n"

echo "== CORS preflight check =="
curl -s -i -X OPTIONS "$BASE/api/v1/chat" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" | grep -i "access-control\|HTTP"

echo -e "\nDone. If every block above returned JSON (not connection errors), the backend is working."
