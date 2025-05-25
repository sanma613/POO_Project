import pygame
import os
import time
from stable_baselines3 import DQN
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.monitor import Monitor

import sys

sys.path.append("src")

from envs.persecucion_env import PersecucionPygameEnv


def entrenar_modelo_mejorado(modelo_path, timesteps=3000000, modo_ia="hibrido", velocidad_juego=240):
    """
    Entrena un modelo DQN para el juego de persecución con configuración optimizada.
    
    Args:
        modelo_path (str): Ruta donde guardar/cargar el modelo entrenado
        timesteps (int): Número total de pasos de entrenamiento
        modo_ia (str): Tipo de IA a entrenar ("hibrido", "predictivo", "campo_potencial", "genetico")
        velocidad_juego (int): FPS durante el entrenamiento (mayor = más rápido)
        
    Returns:
        DQN: Modelo entrenado
    """
    print("Iniciando entrenamiento con IA avanzada...")

    def make_env():
        """Crea un entorno individual para entrenamiento vectorizado."""
        env = PersecucionPygameEnv(
            render_mode=None, 
            modo_entrenamiento=True,
            modo_ia=modo_ia,
            velocidad_juego=velocidad_juego
        )
        return Monitor(env)

    # Usar múltiples entornos paralelos para acelerar el entrenamiento
    env_vectorizado = make_vec_env(make_env, n_envs=8)

    # Cargar modelo existente o crear uno nuevo
    if os.path.exists(modelo_path + ".zip"):
        print(f"Cargando modelo existente de {modelo_path}.zip")
        modelo = DQN.load(modelo_path, env=env_vectorizado)
    else:
        print("Creando modelo nuevo con parámetros optimizados")
        # Configuración DQN optimizada para juegos de persecución
        modelo = DQN(
            "MlpPolicy", 
            env_vectorizado, 
            verbose=1,
            learning_rate=0.0003,
            buffer_size=300000,
            learning_starts=3000,
            batch_size=128,
            target_update_interval=400,
            train_freq=4,
            gradient_steps=2,
            exploration_fraction=0.25,
            exploration_initial_eps=1.0,
            exploration_final_eps=0.01,
            # Red neuronal con capas densas progresivamente menores
            policy_kwargs=dict(net_arch=[256, 256, 128])
        )

    print(f"Entrenando por {timesteps:,} pasos con modo IA: {modo_ia}")
    modelo.learn(total_timesteps=timesteps, progress_bar=True)

    modelo.save(modelo_path)
    print("Entrenamiento completado y modelo guardado")

    env_vectorizado.close()
    return modelo


def jugar_con_modelo_mejorado(modelo_path, modo_ia="hibrido"):
    """
    Ejecuta el juego usando el modelo entrenado para controlar al enemigo.
    
    Args:
        modelo_path (str): Ruta del modelo entrenado
        modo_ia (str): Modo de IA inicial del enemigo
    """
    print("Iniciando modo de juego avanzado...")
    
    if not os.path.exists(modelo_path + ".zip"):
        print("Error: No se encontró el modelo entrenado.")
        print("Ejecuta primero en modo 'entrenar'")
        return

    # Crear entorno de juego visual
    env_juego = PersecucionPygameEnv(
        render_mode="human", 
        modo_entrenamiento=False,
        modo_ia=modo_ia
    )
    
    modelo = DQN.load(modelo_path)
    print("Modelo cargado correctamente")
    print("ESC para salir\n")

    obs, info = env_juego.reset()
    ejecutando = True
    episodios = 0

    # Loop principal del juego
    while ejecutando:
        # Manejo de eventos pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                ejecutando = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    ejecutando = False
                # Cambio dinámico de modo IA durante el juego
                elif event.key == pygame.K_1:
                    env_juego.cambiar_modo_ia("hibrido")
                elif event.key == pygame.K_2:
                    env_juego.cambiar_modo_ia("predictivo")
                elif event.key == pygame.K_3:
                    env_juego.cambiar_modo_ia("campo_potencial")
                elif event.key == pygame.K_4:
                    env_juego.cambiar_modo_ia("genetico")

        # Predicción determinística del modelo para comportamiento consistente
        action, _states = modelo.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env_juego.step(action)

        # Manejo de fin de episodio
        if terminated:
            episodios += 1
            print(f"¡Atrapado! Episodio {episodios} - Pasos: {info['pasos']} - Efectividad IA: {info['efectividad_ia']:.1%}")
            time.sleep(1.5)  # Pausa breve para mostrar resultado
            obs, info = env_juego.reset()
        elif truncated:
            episodios += 1
            print(f"Escapaste - Episodio {episodios}")
            obs, info = env_juego.reset()

    env_juego.close()
    print("¡Gracias por jugar!")