from fastapi import FastAPI
from playapi import router as playapi_router  # Import the router from playapi

# Create the FastAPI app
app = FastAPI()

# Include the playapi routes
app.include_router(playapi_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)