"""
Servicio de análisis de sentimientos usando Google Gemini.
Migrado desde app/services/sentiment_service.py manteniendo funcionalidad exacta.
"""
from google import genai
from shared.config.settings import settings
from shared.services.logging_config import get_logger
from shared.database import models
from sqlalchemy.orm import Session
import time
from typing import Dict, Any

logger = get_logger(__name__)

# Configurar la API de Google
try:
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
except Exception as e:
    logger.error(f"Error al configurar el cliente de Gemini: {e}")
    client = None

def analyze_sentiment_text(text: str) -> float:
    """
    Analiza el sentimiento de un titular y devuelve una puntuación de -1.0 a 1.0.
    """
    if not client:
        logger.warning("El cliente de Gemini no está disponible. Saltando análisis.")
        return 0.0

    prompt = f"""
    Analiza el sentimiento del siguiente titular de noticias sobre criptomonedas.
    Considera el contexto del mercado cripto donde noticias sobre regulaciones o hacks son negativas, y noticias sobre adopción o avances tecnológicos son positivas.
    Responde únicamente con un número decimal entre -1.0 (extremadamente negativo) y 1.0 (extremadamente positivo).
    No añadas absolutamente ninguna explicación, solo el número.

    Titular: "{text}"
    Sentimiento (solo el número decimal):
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        # Pequeña pausa para no saturar la API
        time.sleep(1) 
        
        # Verificar que la respuesta tiene contenido
        if not response.text or response.text.strip() == "":
            logger.warning(f"Respuesta vacía del modelo para el texto: '{text}'")
            return 0.0
            
        score_text = response.text.strip()
        score = float(score_text)
        return max(-1.0, min(1.0, score))
    except ValueError as e:
        logger.error(f"Error al convertir la respuesta a número para el texto: '{text}'. Respuesta: '{response.text if response.text else 'None'}'. Error: {e}")
        return 0.0
    except Exception as e:
        logger.error(f"Error al analizar sentimiento para el texto: '{text}'. Error: {e}")
        return 0.0  # Devolver un sentimiento neutral en caso de error 

def analyze_sentiment(db: Session) -> Dict[str, Any]:
    """
    Analiza sentimientos de noticias no procesadas en la base de datos.
    Retorna un diccionario con el resultado del procesamiento.
    """
    try:
        # Buscar noticias sin análisis de sentimiento
        noticias_sin_analizar = db.query(models.Noticia).filter(
            models.Noticia.sentiment_score == None
        ).limit(60).all()  # Limitamos a 60 por ciclo para no exceder cuotas de API
        
        if not noticias_sin_analizar:
            return {
                "success": True,
                "message": "No hay noticias nuevas para analizar",
                "analyzed_posts": 0
            }

        logger.info(f"Analizando {len(noticias_sin_analizar)} noticias...")
        analyzed_count = 0
        
        for noticia in noticias_sin_analizar:
            try:
                score = analyze_sentiment_text(str(noticia.headline))
                setattr(noticia, 'sentiment_score', score)
                analyzed_count += 1
            except Exception as e:
                logger.error(f"Error analizando noticia {noticia.id}: {e}")
                continue
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Análisis de sentimiento completado. {analyzed_count} noticias procesadas.",
            "analyzed_posts": analyzed_count
        }
        
    except Exception as e:
        logger.error(f"Error en análisis de sentimientos: {e}")
        return {
            "success": False,
            "error": str(e),
            "analyzed_posts": 0
        } 