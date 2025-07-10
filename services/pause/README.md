# Servicios Pausados

Esta carpeta contiene los servicios que han sido pausados temporalmente mientras se cambia el enfoque del proyecto.

## Servicios Pausados

### 1. Grid Trading Bot (`grid/`)
- **Estado**: Pausado
- **Razón**: Cambio de enfoque a Bitsgap para trading automático
- **Funcionalidad**: Trading automático con estrategia de grid
- **Puerto**: 8002

### 2. Trend Following Bot (`trend/`)
- **Estado**: Pausado  
- **Razón**: Cambio de enfoque a Bitsgap para trading automático
- **Funcionalidad**: Bot de seguimiento de tendencias
- **Puerto**: 8005

## Nuevo Enfoque

El proyecto ahora se enfoca en:
- **Brain**: Motor de decisiones y asistente IA
- **News**: Análisis de noticias y sentimientos
- **Hype**: Detección de eventos de hype

Los bots de trading se manejarán a través de **Bitsgap** de forma manual, mientras que el cerebro actuará como asistente IA para tomar decisiones informadas.

## Reactivación

Para reactivar estos servicios en el futuro:
1. Mover las carpetas de vuelta a `services/`
2. Actualizar `docker-compose.yml` para incluir los servicios
3. Verificar compatibilidad con el nuevo enfoque del cerebro 