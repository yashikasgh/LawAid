from fastapi import FastAPI

app = FastAPI(title="LawAid Backend")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "LawAid backend"}
