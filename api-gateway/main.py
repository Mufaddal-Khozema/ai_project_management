from fastapi import FastAPI,Path, Request
import httpx

app= FastAPI()

AUTH_SERVICE_URL = "http://auth-service:8001"
TASK_SERVICE_URL = "http://task-service:8002"

@app.get("/health")
async def health_check():
    return{"Status":"Api gateway is running"}

@app.api_route("/auth/{path:path}", methods=["GET","POST","PUT","DELETE"])
async def auth_gateway(path: str, request:Request):
    url = f"{AUTH_SERVICE_URL}/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers= dict(request.headers),
            content=await request.body()
        )
    return response.json()

@app.api_route("/tasks/{path:path}", methods=["GET","POST", "PUT","DELETE"])
async def task_gateway(path:str, request:Request):
    url = f"{TASK_SERVICE_URL}/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers= dict(request.headers),
            content=await request.body()
        )
    return response.json()