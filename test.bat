@echo off
echo Testing /healthz endpoint...
curl http://localhost:8000/healthz
echo.
echo.

echo Testing /scrape with example.com...
curl -X POST http://localhost:8000/scrape -H "Content-Type: application/json" -d "{\"url\": \"https://example.com\"}" > test_result.json
echo Response saved to test_result.json
echo.

echo Done! Check test_result.json for the response.
