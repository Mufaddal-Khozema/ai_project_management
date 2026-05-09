from fastapi import FastAPI,Path, Request
import httpx

app= FastAPI()

AUTH_SERVICE_URL = "http://localhost:8001"
ORG_SERVICE_URL = "http://localhost:8002"

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

@app.api_route("/org/{path:path}", methods=["GET","POST", "PUT","DELETE"])
async def org_gateway(path:str, request:Request):
    url = f"{ORG_SERVICE_URL}/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers= dict(request.headers),
            content=await request.body()
        )
    return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)