from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db import session, models
from app.tasks.news_collector import scheduler, run_collection_job
from app.services import cryptopanic_service

# Crear las tablas en la base de datos al iniciar (si no existen)
models.Base.metadata.create_all(bind=session.engine)

# --- Gestor de Ciclo de Vida de la Aplicación ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando la aplicación y el scheduler...")
    try:
        scheduler.start()
        print("✅ Scheduler iniciado correctamente")
    except Exception as e:
        print(f"❌ Error al iniciar el scheduler: {e}")
    
    yield
    
    # Shutdown
    print("🛑 Cerrando la aplicación...")
    try:
        if scheduler.running:
            print("🔄 Deteniendo el scheduler...")
            scheduler.shutdown(wait=True)
            print("✅ Scheduler detenido correctamente")
        else:
            print("ℹ️ El scheduler ya estaba detenido")
    except Exception as e:
        print(f"❌ Error al detener el scheduler: {e}")
    finally:
        print("👋 Aplicación cerrada")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan
)

# --- Dependencia para la sesión de DB ---
def get_db():
    db = session.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints de la API ---
@app.get("/", tags=["Status"])
def read_root():
    """Endpoint principal para verificar que la API está viva."""
    return {"status": "El Oráculo está vivo y escuchando."}

@app.post("/tasks/trigger-collection", tags=["Tasks"])
def trigger_collection(db: Session = Depends(get_db)):
    """
    Endpoint para disparar manualmente la recolección de noticias.
    Útil para pruebas y debugging.
    """
    print("🚀 Disparando la recolección de noticias manualmente...")
    result = cryptopanic_service.fetch_and_store_posts(db)
    
    if result["success"]:
        return {
            "status": "success",
            "message": result["message"],
            "new_posts": result.get("new_posts", 0),
            "total_posts": result.get("total_posts", 0)
        }
    else:
        # Retorna error HTTP apropiado pero sin romper la API
        return {
            "status": "error",
            "message": f"Error en la recolección: {result['error']}",
            "error_details": result["error"]
        } 