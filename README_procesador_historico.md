# Procesador de Datos Históricos de Reddit

Este script procesa archivos masivos de datos históricos de Reddit (.zst) y los enriquece con análisis de sentimiento multi-factorial usando la API de Google Gemini.

## Características Principales

- **Eficiencia de Memoria**: Procesamiento en streaming (línea por línea) para manejar archivos de cientos de GB
- **Eficiencia de Base de Datos**: Inserción en lotes para maximizar el rendimiento
- **Robustez**: Manejo inteligente de errores de API con exponential backoff
- **Progreso Visual**: Barra de progreso con `tqdm` para monitorear el avance
- **Filtros de Calidad**: Pipeline completo de filtros para asegurar relevancia de los datos

## Instalación

1. Asegúrate de tener las dependencias instaladas:
```bash
pip install -r requirements.txt
```

2. Configura las variables de entorno en tu archivo `.env`:
```env
DATABASE_URL=postgresql://usuario:contraseña@host:puerto/database
GOOGLE_API_KEY=tu_api_key_de_gemini
```

## Uso

```bash
python procesador_historico.py archivo_reddit.zst
```

### Ejemplo
```bash
python procesador_historico.py data/RS_2023-01.zst
```

## Pipeline de Filtrado

El script aplica los siguientes filtros en orden:

### 1. Filtro de Relevancia de Subreddit
Procesa solo posts de subreddits relacionados con criptomonedas:
- `CryptoCurrency`, `Bitcoin`, `ethereum`, `ethtrader`, `defi`
- `CryptoMoonShots`, `SatoshiStreetBets`, `altcoin`
- `CryptoCurrencyTrading`, `CryptoMarkets`, `binance`, etc.

### 2. Filtro de Calidad Básica
Descarta posts que:
- Tienen texto `[deleted]` o `[removed]`
- Son posts fijados (`stickied`)

### 3. Filtro de Engagement Mínimo
Requiere un score mínimo de 10 puntos

### 4. Filtro por Tipo de Post

#### Posts de Texto (`is_self = True`)
- Requiere que el `selftext` tenga más de 150 caracteres
- Analiza `title + selftext`

#### Posts de Enlace (`is_self = False`)
- Requiere que el dominio esté en la lista blanca de noticias confiables
- Analiza solo el `title`

**Dominios confiables incluidos:**
- `coindesk.com`, `cointelegraph.com`, `decrypt.co`
- `bloomberg.com`, `reuters.com`, `cnbc.com`, `forbes.com`
- `coinbase.com`, `kraken.com`, `binance.com`, etc.

## Análisis de Sentimiento

El script utiliza el modelo `gemini-2.0-flash-lite` para analizar cada post y obtener:

### Campos Analizados
- **sentiment_score**: Float entre -1.0 y 1.0
- **primary_emotion**: Una de: `Euforia`, `Optimismo`, `Neutral`, `Incertidumbre`, `Miedo`
- **news_category**: Una de: `Regulación`, `Tecnología/Adopción`, `Mercado/Trading`, `Seguridad`, `Macroeconomía`

### Criterios de Evaluación

#### Sentiment Score
- **0.6 a 1.0**: Muy positivo (adopción masiva, ATH, buenas regulaciones)
- **0.1 a 0.5**: Positivo (desarrollos, adopción gradual)
- **-0.1 a 0.1**: Neutral (informativo, sin impacto claro)
- **-0.5 a -0.1**: Negativo (regulaciones adversas, caídas)
- **-1.0 a -0.6**: Muy negativo (hacks, prohibiciones, crisis)

#### Primary Emotion
- **Euforia**: ATH, adopción masiva, noticias revolucionarias
- **Optimismo**: Desarrollos positivos, buenas noticias graduales
- **Neutral**: Noticias informativas sin carga emocional
- **Incertidumbre**: Rumores, decisiones pendientes, noticias ambiguas
- **Miedo**: Regulaciones adversas, hacks, crisis, caídas abruptas

## Configuración

### Parámetros del Script
```python
BATCH_SIZE = 500              # Tamaño del lote para inserción en BD
MAX_RETRIES = 5               # Máximo número de reintentos para API
INITIAL_RETRY_DELAY = 5       # Delay inicial para exponential backoff
```

### Manejo de Rate Limits
El script implementa una estrategia de exponential backoff:
- Intento 1: 5 segundos
- Intento 2: 10 segundos
- Intento 3: 20 segundos
- Intento 4: 40 segundos
- Intento 5: 80 segundos

## Salida del Script

### Progreso en Tiempo Real
```
Procesando posts: 45%|████▌     | 45023/100000 [05:23<06:36, 138.2posts/s]
```

### Estadísticas Finales
```
==========================================================
PROCESAMIENTO COMPLETADO
==========================================================
Tiempo total: 3847.52 segundos
Posts leídos: 1,250,000
Posts procesados: 15,750
Lotes insertados: 32
Errores: 147

FILTROS APLICADOS:
  - Subreddit irrelevante: 847,253
  - Baja calidad: 125,847
  - Poco engagement: 186,432
  - Texto muy corto: 45,621
  - Enlace no confiable: 29,950
==========================================================
```

### Archivos de Log
- **Consola**: Salida en tiempo real con progreso
- **procesador_historico.log**: Log completo con timestamps

## Estructura de la Base de Datos

Los datos se insertan en la tabla `noticias` con el siguiente esquema:

```sql
CREATE TABLE noticias (
    id SERIAL PRIMARY KEY,
    source VARCHAR NOT NULL,           -- 'reddit_historical'
    headline TEXT NOT NULL,            -- Texto analizado
    url VARCHAR UNIQUE,                -- URL del post o permalink
    published_at VARCHAR NOT NULL,     -- Timestamp del post
    sentiment_score FLOAT,             -- Score de sentimiento
    primary_emotion VARCHAR,           -- Emoción principal
    news_category VARCHAR              -- Categoría de la noticia
);
```

## Solución de Problemas

### Error: "GOOGLE_API_KEY no configurada"
Asegúrate de tener la clave de API de Gemini en tu archivo `.env`

### Error: "DATABASE_URL no configurada"
Verifica que la URL de la base de datos Neon esté correctamente configurada

### Error: "Rate limit alcanzado"
El script maneja automáticamente los rate limits. Si persiste, considera aumentar `INITIAL_RETRY_DELAY`

### Memoria insuficiente
El script está diseñado para usar memoria mínima. Si tienes problemas, reduce `BATCH_SIZE`

## Consideraciones de Rendimiento

- **RAM**: Uso mínimo gracias al streaming
- **CPU**: Intensivo durante el análisis de IA
- **Red**: Dependiente de la latencia con Gemini API
- **Disco**: Requiere espacio para logs temporales

**Tiempo estimado**: 1-2 horas por millón de posts (dependiendo de los filtros) 