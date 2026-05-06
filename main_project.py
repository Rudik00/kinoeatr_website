import uvicorn
from logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
