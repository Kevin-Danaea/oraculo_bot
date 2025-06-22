"""
Servicio de CryptoPanic para recopilación de noticias (DEPRECATED).
Migrado desde app/services/cryptopanic_service.py manteniendo funcionalidad exacta.
Actualmente se usa Reddit, pero se mantiene para compatibilidad.
"""
import requests
import time
from sqlalchemy.orm import Session
from shared.services.logging_config import get_logger
from shared.database import models
from shared.config.settings import settings

logger = get_logger(__name__)

def fetch_and_store_posts(db: Session):
    """
    Obtiene los posts de la API de CryptoPanic y los guarda en la base de datos,
    evitando duplicados. Incluye manejo robusto de errores y rate limiting.
    """
    try:
        # Verificar que tenemos API Key
        if not settings.CRYPTOPANIC_API_KEY:
            logger.warning("⚠️ No se ha configurado CRYPTOPANIC_API_KEY")
            return {"success": False, "error": "API Key no configurada"}

        # Parámetros para la API
        params = {
            "auth_token": settings.CRYPTOPANIC_API_KEY,
            "public": "true"
        }
        
        logger.info("🔄 Conectando con CryptoPanic API...")
        
        # Configurar timeout y headers
        headers = {
            'User-Agent': 'Oraculo-Bot/1.0',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            settings.CRYPTOPANIC_API_URL, 
            params=params, 
            headers=headers,
        )
        
        # Logging del status code para debugging
        logger.info(f"📡 Status Code: {response.status_code}")
        
        # Manejo específico de errores HTTP
        if response.status_code == 502:
            logger.error("❌ Error 502 Bad Gateway - CryptoPanic tiene problemas de servidor")
            return {"success": False, "error": "CryptoPanic 502 Bad Gateway"}
        elif response.status_code == 429:
            logger.warning("⏰ Rate limit alcanzado - esperando antes del siguiente intento")
            return {"success": False, "error": "Rate limit exceeded"}
        elif response.status_code == 403:
            logger.error("🔑 Error 403 - Verifica tu API Key de CryptoPanic")
            return {"success": False, "error": "API Key inválida o sin permisos"}
        elif response.status_code >= 500:
            logger.error(f"🔧 Error del servidor CryptoPanic: {response.status_code}")
            return {"success": False, "error": f"Server error {response.status_code}"}
        
        # Verificar si la respuesta es exitosa
        response.raise_for_status()
        
        # Intentar parsear JSON
        try:
            data = response.json()
        except ValueError as e:
            logger.error(f"❌ Error al parsear JSON: {e}")
            return {"success": False, "error": "Respuesta JSON inválida"}
        
        posts = data.get("results", [])
        
        if not posts:
            logger.info("ℹ️ No se encontraron posts en la respuesta")
            return {"success": True, "new_posts": 0, "message": "No hay posts nuevos"}
        
        new_posts_count = 0
        
        for post in posts:
            try:
                # Extraer campos requeridos con valores por defecto
                post_id = post.get('id')
                title = post.get('title', 'Sin título')
                slug = post.get('slug', '')
                published_at = post.get('published_at', post.get('created_at', ''))
                
                # Construir URL completa basada en el slug
                if slug:
                    full_url = f"https://cryptopanic.com/news/{post_id}/{slug}/"
                elif post_id:
                    full_url = f"https://cryptopanic.com/news/{post_id}/"
                else:
                    logger.warning("⚠️ Post sin ID ni slug válido, omitiendo")
                    continue
                
                # Comprobar si la noticia ya existe por su URL para evitar duplicados
                existing_post = db.query(models.Noticia).filter(models.Noticia.url == full_url).first()
                if not existing_post:
                    new_post = models.Noticia(
                        source="CryptoPanic",
                        headline=title,
                        url=full_url,
                        published_at=published_at
                    )
                    db.add(new_post)
                    new_posts_count += 1
                    logger.info(f"📰 Nueva noticia: {title[:50]}...")
                else:
                    logger.debug(f"🔄 Noticia existente: {title[:30]}...")
                    
            except Exception as e:
                logger.error(f"⚠️ Error procesando post: {e}")
                logger.debug(f"📋 Datos del post problemático: {post}")
                continue
        
        db.commit()
        logger.info(f"✅ Recolección completada. Se añadieron {new_posts_count} posts nuevos de {len(posts)} disponibles.")
        
        return {
            "success": True, 
            "new_posts": new_posts_count, 
            "total_posts": len(posts),
            "message": f"Se añadieron {new_posts_count} posts nuevos"
        }
        
    except requests.exceptions.Timeout:
        logger.error("⏱️ Timeout al conectar con CryptoPanic API")
        db.rollback()
        return {"success": False, "error": "Timeout de conexión"}
    except requests.exceptions.ConnectionError:
        logger.error("🔌 Error de conexión con CryptoPanic API")
        db.rollback()
        return {"success": False, "error": "Error de conexión"}
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Error en la petición HTTP: {e}")
        db.rollback()
        return {"success": False, "error": f"Error HTTP: {str(e)}"}
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        db.rollback()
        return {"success": False, "error": f"Error inesperado: {str(e)}"} 