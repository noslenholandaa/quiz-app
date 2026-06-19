from app.main import app

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    import logging
    logger = logging.getLogger("quizapp")
    logger.info("Servidor iniciando na porta %s", port)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
