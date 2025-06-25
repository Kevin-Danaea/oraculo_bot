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
import json
from typing import Dict, Any

logger = get_logger(__name__)

# Listas de vocabulario controlado para validación
VALID_EMOTIONS = ['Euforia', 'Optimismo', 'Neutral', 'Incertidumbre', 'Miedo']
VALID_CATEGORIES = ['Regulación', 'Tecnología/Adopción', 'Mercado/Trading', 'Seguridad', 'Macroeconomía']

# Configurar la API de Google
try:
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
except Exception as e:
    logger.error(f"Error al configurar el cliente de Gemini: {e}")
    client = None

def analyze_sentiment_text(text: str) -> Dict[str, Any]:
    """
    Analiza el sentimiento de un titular y devuelve un diccionario con análisis completo.
    
    Returns:
        Dict con keys: sentiment_score (float), primary_emotion (str), news_category (str)
    """
    if not client:
        logger.warning("El cliente de Gemini no está disponible. Saltando análisis.")
        return {
            "sentiment_score": 0.0,
            "primary_emotion": "Neutral",
            "news_category": "Mercado/Trading"
        }

    prompt = f"""
    Analiza el siguiente titular de noticias sobre criptomonedas y devuelve ÚNICAMENTE un JSON válido con la siguiente estructura:
    
    {{
        "sentiment_score": float entre -1.0 y 1.0,
        "primary_emotion": "una de estas opciones EXACTAS: Euforia, Optimismo, Neutral, Incertidumbre, Miedo",
        "news_category": "una de estas opciones EXACTAS: Regulación, Tecnología/Adopción, Mercado/Trading, Seguridad, Macroeconomía"
    }}
    
    CRITERIOS PARA SENTIMENT_SCORE (El QUÉ - ¿Es buena, mala o neutra?):
    - Noticias muy positivas (adopción masiva, ATH, buenas regulaciones): 0.6 a 1.0
    - Noticias positivas (desarrollos, adopción gradual): 0.1 a 0.5
    - Noticias neutras (informativas, sin impacto claro): -0.1 a 0.1
    - Noticias negativas (regulaciones adversas, caídas): -0.5 a -0.1
    - Noticias muy negativas (hacks, prohibiciones, crisis): -1.0 a -0.6
    
    CRITERIOS PARA PRIMARY_EMOTION (El CÓMO - ¿Cómo reacciona el mercado?):
    - Euforia: ATH, adopción masiva, noticias revolucionarias
    - Optimismo: Desarrollos positivos, buenas noticias graduales
    - Neutral: Noticias informativas sin carga emocional
    - Incertidumbre: Rumores, decisiones pendientes, noticias ambiguas
    - Miedo: Regulaciones adversas, hacks, crisis, caídas abruptas
    
    CRITERIOS PARA NEWS_CATEGORY (El PORQUÉ - ¿Cuál es el tema?):
    - Regulación: Leyes, normativas, decisiones gubernamentales, compliance
    - Tecnología/Adopción: Avances técnicos, nuevas integraciones, adopción institucional
    - Mercado/Trading: Precios, análisis técnico, movimientos de mercado, ETFs
    - Seguridad: Hacks, vulnerabilidades, protocolos de seguridad
    - Macroeconomía: Inflación, política monetaria, economía global, correlaciones
    
    Titular: "{text}"
    
    Responde ÚNICAMENTE con el JSON, sin explicaciones adicionales:
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        # Pequeña pausa para no saturar la API
        time.sleep(2) 
        
        # Verificar que la respuesta tiene contenido
        if not response.text or response.text.strip() == "":
            logger.warning(f"Respuesta vacía del modelo para el texto: '{text}'")
            return {
                "sentiment_score": 0.0,
                "primary_emotion": "Neutral",
                "news_category": "Mercado/Trading"
            }
            
        # Limpiar la respuesta de posibles bloques de código markdown
        response_text = response.text.strip()
        
        # Si la respuesta viene en bloques de código, extraer solo el JSON
        if response_text.startswith('```json'):
            # Extraer contenido entre ```json y ```
            start_marker = '```json\n'
            end_marker = '\n```'
            start_index = response_text.find(start_marker)
            end_index = response_text.find(end_marker)
            
            if start_index != -1 and end_index != -1:
                start_index += len(start_marker)
                response_text = response_text[start_index:end_index]
        elif response_text.startswith('```'):
            # Si empieza con ``` sin json, buscar el primer bloque
            lines = response_text.split('\n')
            if len(lines) > 1:
                response_text = '\n'.join(lines[1:-1])  # Quitar primera y última línea
        
        # Intentar parsear el JSON de la respuesta
        try:
            result = json.loads(response_text.strip())
            
            # Validar y limpiar la respuesta
            sentiment_score = float(result.get("sentiment_score", 0.0))
            sentiment_score = max(-1.0, min(1.0, sentiment_score))  # Clamp entre -1 y 1
            
            primary_emotion = result.get("primary_emotion", "Neutral")
            if primary_emotion not in VALID_EMOTIONS:
                logger.warning(f"Emoción inválida '{primary_emotion}', usando 'Neutral'")
                primary_emotion = "Neutral"
            
            news_category = result.get("news_category", "Mercado/Trading")
            if news_category not in VALID_CATEGORIES:
                logger.warning(f"Categoría inválida '{news_category}', usando 'Mercado/Trading'")
                news_category = "Mercado/Trading"
            
            return {
                "sentiment_score": sentiment_score,
                "primary_emotion": primary_emotion,
                "news_category": news_category
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON de Gemini para el texto: '{text}'. Respuesta: '{response.text}'. Error: {e}")
            return {
                "sentiment_score": 0.0,
                "primary_emotion": "Neutral",
                "news_category": "Mercado/Trading"
            }
            
    except Exception as e:
        logger.error(f"Error al analizar sentimiento para el texto: '{text}'. Error: {e}")
        return {
            "sentiment_score": 0.0,
            "primary_emotion": "Neutral",
            "news_category": "Mercado/Trading"
        }

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
                # Obtener análisis completo
                analysis_result = analyze_sentiment_text(str(noticia.headline))
                
                # Actualizar todos los campos en la base de datos
                noticia.sentiment_score = analysis_result["sentiment_score"]
                noticia.primary_emotion = analysis_result["primary_emotion"]
                noticia.news_category = analysis_result["news_category"]
                
                analyzed_count += 1
                logger.info(f"📊 Análisis completado: '{noticia.headline[:50]}...' → Score: {analysis_result['sentiment_score']:.2f}, Emoción: {analysis_result['primary_emotion']}, Categoría: {analysis_result['news_category']}")
                
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
