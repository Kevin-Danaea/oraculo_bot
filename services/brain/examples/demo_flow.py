#!/usr/bin/env python3
"""
Demo del Flujo Completo del Brain Service
==========================================

Este script demuestra cómo funciona el brain service en diferentes escenarios.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# Simulación de la base de datos
class MockDatabase:
    """Base de datos simulada para demostración."""
    
    def __init__(self):
        self.estrategia_status = []
        self.noticias = []
    
    def add_decision(self, decision: Dict[str, Any]):
        """Agrega una decisión a la base de datos."""
        self.estrategia_status.append(decision)
        print(f"💾 Decisión guardada en BD: {decision['par']} -> {decision['decision']}")
    
    def get_latest_decision(self, pair: str, estrategia: str = 'GRID'):
        """Obtiene la última decisión para un par."""
        for decision in reversed(self.estrategia_status):
            if decision['par'] == pair and decision['estrategia'] == estrategia:
                return decision
        return None
    
    def get_decisions_stats(self):
        """Obtiene estadísticas de decisiones."""
        stats = {}
        for decision in self.estrategia_status:
            decision_type = decision['decision']
            if decision_type not in stats:
                stats[decision_type] = 0
            stats[decision_type] += 1
        return stats

# Simulación del brain service
class MockBrainService:
    """Servicio brain simulado para demostración."""
    
    def __init__(self, db: MockDatabase):
        self.db = db
        self.cycle_count = 0
        self.supported_pairs = ['ETH/USDT', 'BTC/USDT', 'AVAX/USDT']
        self.recipes = {
            'ETH/USDT': {'adx_threshold': 30, 'volatility_threshold': 0.025, 'sentiment_threshold': 0.5},
            'BTC/USDT': {'adx_threshold': 25, 'volatility_threshold': 0.035, 'sentiment_threshold': 0.5},
            'AVAX/USDT': {'adx_threshold': 35, 'volatility_threshold': 0.020, 'sentiment_threshold': 0.5}
        }
    
    async def simulate_market_data(self, pair: str) -> Dict[str, Any]:
        """Simula obtención de datos de mercado."""
        # Simular datos reales con variación
        import random
        
        base_data = {
            'ETH/USDT': {'adx': 25, 'volatility': 0.028, 'sentiment': 0.65},
            'BTC/USDT': {'adx': 32, 'volatility': 0.031, 'sentiment': 0.55},
            'AVAX/USDT': {'adx': 28, 'volatility': 0.022, 'sentiment': 0.70}
        }
        
        # Agregar variación aleatoria
        data = base_data[pair].copy()
        data['adx'] += random.uniform(-5, 5)
        data['volatility'] += random.uniform(-0.005, 0.005)
        data['sentiment'] += random.uniform(-0.1, 0.1)
        
        return data
    
    def make_decision(self, pair: str, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Toma una decisión basada en indicadores."""
        recipe = self.recipes[pair]
        
        # Evaluar condiciones
        adx_ok = indicators['adx'] < recipe['adx_threshold']
        volatility_ok = indicators['volatility'] > recipe['volatility_threshold']
        sentiment_ok = indicators['sentiment'] > recipe['sentiment_threshold']
        detalles = []
        detalles.append(f"ADX={indicators['adx']:.2f} < {recipe['adx_threshold']}" if adx_ok else f"ADX={indicators['adx']:.2f} >= {recipe['adx_threshold']}")
        detalles.append(f"Volatilidad={indicators['volatility']:.4f} > {recipe['volatility_threshold']:.4f}" if volatility_ok else f"Volatilidad={indicators['volatility']:.4f} <= {recipe['volatility_threshold']:.4f}")
        detalles.append(f"Sentimiento={indicators['sentiment']:.3f} > {recipe['sentiment_threshold']:.3f}" if sentiment_ok else f"Sentimiento={indicators['sentiment']:.3f} <= {recipe['sentiment_threshold']:.3f}")
        if adx_ok and volatility_ok and sentiment_ok:
            decision = 'OPERAR_GRID'
            reason = f"Condiciones favorables: {'; '.join(detalles)}"
        else:
            decision = 'PAUSAR_GRID'
            reason = f"Condiciones desfavorables: {'; '.join(detalles)}"
        
        return {
            'par': pair,
            'estrategia': 'GRID',
            'decision': decision,
            'razon': reason,
            'adx_actual': indicators['adx'],
            'volatilidad_actual': indicators['volatility'],
            'sentiment_promedio': indicators['sentiment'],
            'umbral_adx': recipe['adx_threshold'],
            'umbral_volatilidad': recipe['volatility_threshold'],
            'umbral_sentimiento': recipe['sentiment_threshold'],
            'timestamp': datetime.utcnow()
        }
    
    async def run_analysis_batch(self):
        """Ejecuta análisis batch de todos los pares."""
        self.cycle_count += 1
        print(f"\n🚀 ========== ANÁLISIS BATCH CICLO {self.cycle_count} ==========")
        print(f"📊 Analizando {len(self.supported_pairs)} pares: {', '.join(self.supported_pairs)}")
        
        decisions_made = 0
        successful_pairs = 0
        
        for pair in self.supported_pairs:
            try:
                print(f"\n📈 Analizando {pair}...")
                
                # Simular obtención de datos
                print(f"📊 Obteniendo datos para {pair}...")
                indicators = await self.simulate_market_data(pair)
                print(f"✅ Datos obtenidos: ADX={indicators['adx']:.2f}, Vol={indicators['volatility']:.4f}, Sentiment={indicators['sentiment']:.2f}")
                
                # Tomar decisión
                decision = self.make_decision(pair, indicators)
                
                # Guardar decisión
                self.db.add_decision(decision)
                
                # Mostrar resultado
                print(f"✅ {pair}: {decision['decision']} - {decision['razon']}")
                
                decisions_made += 1
                successful_pairs += 1
                
            except Exception as e:
                print(f"❌ Error analizando {pair}: {e}")
        
        print(f"\n🎯 ========== ANÁLISIS BATCH COMPLETADO ==========")
        print(f"✅ Pares exitosos: {successful_pairs}/{len(self.supported_pairs)}")
        print(f"📊 Decisiones tomadas: {decisions_made}")
        print(f"🔄 Ciclo: {self.cycle_count}")
        
        return decisions_made

# Simulación del GRID bot
class MockGridBot:
    """Bot GRID simulado para demostración."""
    
    def __init__(self, db: MockDatabase):
        self.db = db
        self.active_pairs = set()
        self.last_check = datetime.utcnow() - timedelta(hours=2)
    
    def check_brain_decisions(self):
        """Verifica las decisiones del brain."""
        print(f"\n🤖 ========== GRID BOT - VERIFICANDO DECISIONES ==========")
        print(f"⏰ Última verificación: {self.last_check}")
        
        pairs_to_check = ['ETH/USDT', 'BTC/USDT', 'AVAX/USDT']
        
        for pair in pairs_to_check:
            decision = self.db.get_latest_decision(pair)
            
            if not decision:
                print(f"❌ No hay decisión para {pair}")
                continue
            
            # Verificar si la decisión es reciente
            if decision['timestamp'] > self.last_check:
                print(f"\n📊 Nueva decisión para {pair}:")
                print(f"   🤖 Decisión: {decision['decision']}")
                print(f"   📝 Razón: {decision['razon']}")
                print(f"   📈 ADX: {decision['adx_actual']:.2f}")
                print(f"   📊 Volatilidad: {decision['volatilidad_actual']:.4f}")
                print(f"   ⏰ Timestamp: {decision['timestamp']}")
                
                # Tomar acción
                if decision['decision'] == 'OPERAR_GRID':
                    if pair not in self.active_pairs:
                        print(f"🚀 Iniciando GRID bot para {pair}")
                        self.active_pairs.add(pair)
                    else:
                        print(f"✅ GRID bot ya activo para {pair}")
                elif decision['decision'] == 'PAUSAR_GRID':
                    if pair in self.active_pairs:
                        print(f"⏸️ Pausando GRID bot para {pair}")
                        self.active_pairs.remove(pair)
                    else:
                        print(f"✅ GRID bot ya pausado para {pair}")
                elif decision['decision'] == 'ERROR':
                    print(f"⚠️ Error en brain para {pair}: {decision['razon']}")
                    print("🔄 Manteniendo estado actual del bot")
            else:
                print(f"ℹ️ No hay nuevas decisiones para {pair}")
        
        self.last_check = datetime.utcnow()
        print(f"\n📋 Estado actual de bots activos: {list(self.active_pairs) if self.active_pairs else 'Ninguno'}")

# Función principal de demostración
async def run_demo():
    """Ejecuta la demostración completa del flujo."""
    print("🎯 ========== DEMO: FLUJO COMPLETO DEL BRAIN SERVICE ==========")
    print("🧠 Simulando el funcionamiento del brain service y su integración con bots")
    
    # Inicializar componentes
    db = MockDatabase()
    brain = MockBrainService(db)
    grid_bot = MockGridBot(db)
    
    # Escenario 1: Primer análisis
    print("\n" + "="*60)
    print("🎯 ESCENARIO 1: PRIMER ANÁLISIS DEL BRAIN")
    print("="*60)
    
    await brain.run_analysis_batch()
    
    # GRID bot verifica decisiones
    grid_bot.check_brain_decisions()
    
    # Mostrar estadísticas
    stats = db.get_decisions_stats()
    print(f"\n📊 Estadísticas de decisiones: {stats}")
    
    # Escenario 2: Cambio de condiciones de mercado
    print("\n" + "="*60)
    print("🎯 ESCENARIO 2: CAMBIO DE CONDICIONES DE MERCADO")
    print("="*60)
    
    print("📈 Simulando cambio en condiciones de mercado...")
    # Modificar datos base para simular cambio
    brain.recipes['ETH/USDT']['adx_threshold'] = 20  # Umbral más estricto
    
    await brain.run_analysis_batch()
    
    # GRID bot verifica nuevas decisiones
    grid_bot.check_brain_decisions()
    
    # Escenario 3: Manejo de errores
    print("\n" + "="*60)
    print("🎯 ESCENARIO 3: MANEJO DE ERRORES")
    print("="*60)
    
    print("❌ Simulando error en obtención de datos...")
    
    # Simular error para BTC/USDT
    original_simulate = brain.simulate_market_data
    
    async def simulate_with_error(pair: str):
        if pair == 'BTC/USDT':
            raise Exception("Connection timeout")
        return await original_simulate(pair)
    
    brain.simulate_market_data = simulate_with_error
    
    await brain.run_analysis_batch()
    
    # Restaurar función original
    brain.simulate_market_data = original_simulate
    
    # Escenario 4: Monitoreo y estadísticas
    print("\n" + "="*60)
    print("🎯 ESCENARIO 4: MONITOREO Y ESTADÍSTICAS")
    print("="*60)
    
    # Health check del brain
    print("🏥 Health Check del Brain Service:")
    print(f"   🏃‍♂️ Ejecutándose: True")
    print(f"   🔄 Ciclo: {brain.cycle_count}")
    print(f"   📊 Total decisiones: {len(db.estrategia_status)}")
    
    # Estadísticas finales
    final_stats = db.get_decisions_stats()
    print(f"\n📈 Estadísticas finales:")
    for decision_type, count in final_stats.items():
        print(f"   {decision_type}: {count}")
    
    # Estado final de bots
    print(f"\n🤖 Estado final de bots:")
    print(f"   Bots activos: {list(grid_bot.active_pairs) if grid_bot.active_pairs else 'Ninguno'}")
    
    # Escenario 5: Preparación para Redis
    print("\n" + "="*60)
    print("🎯 ESCENARIO 5: PREPARACIÓN PARA REDIS")
    print("="*60)
    
    print("📡 Simulando notificaciones Redis...")
    
    # Simular notificación Redis
    latest_decisions = []
    for pair in brain.supported_pairs:
        decision = db.get_latest_decision(pair)
        if decision:
            latest_decisions.append(decision)
    
    for decision in latest_decisions:
        redis_message = {
            'pair': decision['par'],
            'decision': decision['decision'],
            'reason': decision['razon'],
            'indicators': {
                'adx': decision['adx_actual'],
                'volatility': decision['volatilidad_actual'],
                'sentiment': decision['sentiment_promedio']
            },
            'timestamp': decision['timestamp'].isoformat()
        }
        
        print(f"🔔 Notificación Redis para {decision['par']}:")
        print(f"   📊 Decisión: {decision['decision']}")
        print(f"   📝 Razón: {decision['razon']}")
        print(f"   📈 ADX: {decision['adx_actual']:.2f}")
        print(f"   📊 Volatilidad: {decision['volatilidad_actual']:.4f}")
    
    print("\n✅ ========== DEMO COMPLETADA ==========")
    print("🎯 El flujo del brain service está funcionando correctamente!")
    print("🧠 El brain es independiente y publica decisiones en la base de datos")
    print("🤖 Los bots consultan la BD para obtener decisiones")
    print("📡 Preparado para migrar a Redis en el futuro")

if __name__ == "__main__":
    asyncio.run(run_demo()) 