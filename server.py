import uvicorn

if __name__ == "__main__":
    print("Starting AI Cognitive OS FastAPI Backend Server...")
    print("API Documentation available at: http://localhost:8000/docs")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
