"""
Adaptador de Google Gemini para análisis de sentimientos.
Implementación concreta de la interfaz SentimentAnalyzer.
"""
import time
import json
from typing import Dict, Any
from google import genai

from app.domain.interfaces import SentimentAnalyzer
from app.domain.entities import SentimentAnalysis, EmotionType, CategoryType
from shared.config.settings import settings
from shared.services.logging_config import get_logger


logger = get_logger(__name__)


class GeminiSentimentAnalyzer(SentimentAnalyzer):
    """
    Implementación del analizador de sentimientos usando Google Gemini.
    """
    
    def __init__(self):
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa el cliente de Gemini."""
        try:
            if not settings.GOOGLE_API_KEY:
                logger.warning("API Key de Google no configurada")
                return
            
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            logger.info("✅ Cliente de Gemini inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al configurar el cliente de Gemini: {e}")
            self._client = None
    
    def _build_prompt(self, text: str) -> str:
        """Construye el prompt para el análisis de sentimiento."""
        return f"""
        Actúa como un analista cuantitativo de sentimiento, especializado en el mercado de criptomonedas. Tu tarea es evaluar el siguiente texto y devolver un análisis estructurado.

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
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parsea la respuesta de Gemini y extrae el JSON.
        """
        # Limpiar la respuesta
        response_text = response_text.strip()
        
        # Si la respuesta viene en bloques de código, extraer solo el JSON
        if response_text.startswith('```json'):
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
                response_text = '\n'.join(lines[1:-1])
        
        # Intentar parsear el JSON
        return json.loads(response_text.strip())
    
    def _get_default_analysis(self) -> SentimentAnalysis:
        """Retorna un análisis por defecto cuando no se puede analizar."""
        return SentimentAnalysis(
            sentiment_score=0.0,
            primary_emotion=EmotionType.NEUTRAL,
            news_category=CategoryType.MERCADO_TRADING
        )
    
    def analyze_text(self, text: str) -> SentimentAnalysis:
        """
        Analiza el sentimiento de un texto usando Gemini.
        
        Args:
            text: Texto a analizar
            
        Returns:
            SentimentAnalysis con los resultados
        """
        if not self._client:
            logger.warning("Cliente de Gemini no disponible, retornando análisis por defecto")
            return self._get_default_analysis()
        
        try:
            # Generar el prompt
            prompt = self._build_prompt(text)
            
            # Llamar a Gemini
            response = self._client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt
            )
            
            # Pequeña pausa para no saturar la API
            time.sleep(2)
            
            # Verificar respuesta
            if not response.text or response.text.strip() == "":
                logger.warning(f"Respuesta vacía del modelo para el texto: '{text[:50]}...'")
                return self._get_default_analysis()
            
            # Parsear la respuesta
            result = self._parse_response(response.text)
            
            # Validar y convertir el resultado
            sentiment_score = float(result.get("sentiment_score", 0.0))
            sentiment_score = max(-1.0, min(1.0, sentiment_score))  # Clamp entre -1 y 1
            
            # Obtener emoción
            primary_emotion_str = result.get("primary_emotion", "Neutral")
            try:
                primary_emotion = EmotionType(primary_emotion_str)
            except ValueError:
                logger.warning(f"Emoción inválida '{primary_emotion_str}', usando 'Neutral'")
                primary_emotion = EmotionType.NEUTRAL
            
            # Obtener categoría
            news_category_str = result.get("news_category", "Mercado/Trading")
            try:
                news_category = CategoryType(news_category_str)
            except ValueError:
                logger.warning(f"Categoría inválida '{news_category_str}', usando 'Mercado/Trading'")
                news_category = CategoryType.MERCADO_TRADING
            
            return SentimentAnalysis(
                sentiment_score=sentiment_score,
                primary_emotion=primary_emotion,
                news_category=news_category
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON de Gemini para '{text[:50]}...': {e}")
            return self._get_default_analysis()
            
        except Exception as e:
            logger.error(f"Error al analizar sentimiento para '{text[:50]}...': {e}")
            return self._get_default_analysis() 