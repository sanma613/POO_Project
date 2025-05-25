import pygame
import random
import math
import time
import numpy as np
import gymnasium as gym
from gymnasium import spaces

import sys

sys.path.append("src")

from utils.mapa_utils import GeneradorDeMapas
from ia.smart_chase_algorithm import AlgoritmoPersecucionInteligente, calcular_accion_inteligente
from model.agentes import Jugador, Enemigo
from model.entorno import ObstaculoFuturista, PowerUpSalud
from utils.visual_effects import VisualEffects
from utils.pantallas import pantalla_bienvenida, pantalla_game_over

# Global map generator instance for reuse
generador_mapa = GeneradorDeMapas()

class PersecucionPygameEnv(gym.Env):
    """
    Entorno de persecución personalizado para OpenAI Gymnasium, simulando un juego
    donde un jugador es perseguido por enemigos en un mapa con obstáculos.
    Soporta modos de entrenamiento para IA y juego interactivo.
    """
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 60}

    def __init__(self, ancho_pantalla=600, alto_pantalla=400, render_mode=None, 
                 modo_entrenamiento=False, modo_ia="hibrido", velocidad_juego=60, num_enemigos=4):
        """
        Inicializa el entorno de persecución.

        Args:
            ancho_pantalla (int): Ancho de la ventana del juego en píxeles.
            alto_pantalla (int): Alto de la ventana del juego en píxeles.
            render_mode (str): Modo de renderizado ("human" para visualización, "rgb_array" para frames).
            modo_entrenamiento (bool): True si el entorno es para entrenamiento de IA, False para juego normal.
            modo_ia (str): Estrategia de IA para los enemigos ("hibrido", "predictivo", "campo_potencial", "genetico").
            velocidad_juego (int): Velocidad de fotogramas por segundo del juego.
            num_enemigos (int): Número de enemigos en el juego.
        """
        super().__init__()
        self.ancho_pantalla = ancho_pantalla
        self.alto_pantalla = alto_pantalla
        self.render_mode = render_mode
        self.modo_entrenamiento = modo_entrenamiento
        self.modo_ia = modo_ia  # Configura el modo de IA para los enemigos
        self.velocidad_juego = velocidad_juego
        self.num_enemigos = num_enemigos

        self.juego_terminado = False
        self.victoria = False
        self.puntos = 0

        # Define el espacio de observación para la IA.
        # Consiste en datos normalizados de cada enemigo (posición, dirección al jugador, distancia)
        # y la posición normalizada del jugador, más el progreso del paso.
        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(5 * self.num_enemigos + 3,),  # 5 valores por enemigo + 3 del jugador/progreso
            dtype=np.float32
        )

        self.tiempo_ultimo_mapa = [time.time()]  # Usado para actualizar el mapa periódicamente
        self.INTERVALO_MAPA = 15  # Intervalo en segundos para la actualización del mapa

        self.powerups_salud = []
        self.tiempo_ultimo_powerup = time.time()
        self.INTERVALO_POWERUP = 11  # Segundos entre intentos de aparición de power-ups
            
        # Define el espacio de acción para el jugador (si es controlado por una IA externa):
        # 9 acciones: 8 direcciones de movimiento (arriba, abajo, izquierda, derecha, diagonales) + quieto.
        self.action_space = spaces.Discrete(9)

        # Variables de Pygame para renderizado
        self.pantalla = None
        self.clock = None
        self.font = None

        # Componentes del juego
        self.jugador = None
        self.enemigos = []
        self.obstaculos = []
        self.distancia_anterior = None # Usado en el cálculo de recompensas para entrenamiento
        self.pasos = 0
        self.max_pasos = 1500 if self.modo_entrenamiento else float("inf") # Límite de pasos para entrenamiento
        self.score = 0
        self.capturas = 0
        
        # Instancia del algoritmo de IA inteligente para los enemigos
        self.algoritmo_ia = AlgoritmoPersecucionInteligente(ancho_pantalla, alto_pantalla)
        self.usar_ia_inteligente = True  # Controla si los enemigos usan la IA inteligente o la IA de entrenamiento
        
        # Estadísticas de rendimiento (mayormente para depuración o análisis)
        self.tiempo_captura_promedio = []
        self.efectividad_ia = 0.0

    def _get_obs(self):
        """
        Construye el vector de observación para el agente de aprendizaje.
        Normaliza todas las coordenadas y distancias a un rango de [0, 1] o [-1, 1].

        Returns:
            np.array: Un array NumPy que representa el estado actual del entorno.
        """
        # Normaliza la posición del jugador respecto al tamaño de la pantalla
        player_x_norm = self.jugador.x / self.ancho_pantalla
        player_y_norm = self.jugador.y / self.alto_pantalla

        obs_list = []

        for enemigo in self.enemigos:
            # Posición normalizada del enemigo
            ex_norm = enemigo.x / self.ancho_pantalla
            ey_norm = enemigo.y / self.alto_pantalla

            # Vector direccional del enemigo hacia el jugador.
            # Representa la dirección en la que el enemigo debe moverse para alcanzar al jugador.
            dx = self.jugador.x - enemigo.x
            dy = self.jugador.y - enemigo.y
            dist = max(math.hypot(dx, dy), 1.0) # Distancia euclidiana, se asegura que no sea cero

            dir_x = dx / dist # Componente X del vector de dirección normalizado
            dir_y = dy / dist # Componente Y del vector de dirección normalizado

            # Distancia normalizada. Se limita a 1.0 para evitar valores excesivamente grandes.
            dist_norm = min(dist / 300.0, 1.0)

            # Agrega los 5 valores del estado de este enemigo a la lista de observación
            obs_list.extend([ex_norm, ey_norm, dir_x, dir_y, dist_norm])

        # Finalmente, añade la posición del jugador y el progreso del episodio
        prog = self.pasos / self.max_pasos
        obs_list.extend([player_x_norm, player_y_norm, prog])

        return np.array(obs_list, dtype=np.float32)

    def _get_info(self):
        """
        Retorna un diccionario con información adicional sobre el estado del entorno,
        útil para depuración y análisis pero no para la toma de decisiones directas del agente.
        """
        distancias = [
            math.hypot(e.x - self.jugador.x, e.y - self.jugador.y)
            for e in self.enemigos
        ]
        return {
            "distancias": distancias,
            "pasos": self.pasos,
            "capturas": self.capturas,
            "efectividad_ia": self.efectividad_ia,
            "modo_ia": self.modo_ia
        }

    def reset(self, seed=None):
        """
        Reinicia el entorno a su estado inicial.
        Coloca al jugador, enemigos y obstáculos en posiciones válidas sin superposiciones.

        Args:
            seed (int): Semilla para el generador de números aleatorios para reproducibilidad.

        Returns:
            tuple: Observación inicial y diccionario de información.
        """
        super().reset(seed=seed)
        intentos = 0
        jugador_valido = False
        
        # Bucle para encontrar posiciones válidas para el jugador y los enemigos
        while intentos < 200 and not jugador_valido:
            # Posición aleatoria para el jugador
            jugador_x = random.randint(50, self.ancho_pantalla - 50)
            jugador_y = random.randint(50, self.alto_pantalla - 50)
            jugador_rect = pygame.Rect(int(jugador_x - 10), int(jugador_y - 10), 20, 20)

            enemigos_candidatos = []
            valido = True

            # Genera posiciones para los enemigos, asegurando que no colisionen entre sí
            # ni con el jugador, y que estén a una distancia mínima del jugador.
            for _ in range(self.num_enemigos):
                ex = random.randint(50, self.ancho_pantalla - 50)
                ey = random.randint(50, self.alto_pantalla - 50)
                enemigo_rect_temp = pygame.Rect(int(ex - 12), int(ey - 12), 24, 24)

                # No chocar con el jugador
                if enemigo_rect_temp.colliderect(jugador_rect):
                    valido = False
                    break

                # No chocar entre enemigos (mínimo 80 px de separación)
                for (ox, oy) in enemigos_candidatos:
                    if math.hypot(ex - ox, ey - oy) < 80:
                        valido = False
                        break
                if not valido:
                    break

                enemigos_candidatos.append((ex, ey))

            # Cada enemigo debe estar a más de 150 px del jugador para un inicio justo
            if valido:
                for (ex, ey) in enemigos_candidatos:
                    d = math.hypot(ex - jugador_x, ey - jugador_y)
                    if d <= 150:
                        valido = False
                        break

            if valido:
                self.jugador = Jugador(jugador_x, jugador_y)
                self.enemigos = [Enemigo(ex, ey) for (ex, ey) in enemigos_candidatos]
                jugador_valido = True

            intentos += 1

        if not jugador_valido:
            raise RuntimeError("No se encontraron posiciones válidas para jugador y enemigos tras 200 intentos")

        self.obstaculos = []
        
        # Obstáculo central fijo, se verifica que no colisione con agentes
        obstaculo_central = ObstaculoFuturista(
            self.ancho_pantalla // 2 - 40, self.alto_pantalla // 2 - 60, 80, 120
        )
        
        choque_central = False
        if obstaculo_central.rect.colliderect(pygame.Rect(int(self.jugador.x - 10), int(self.jugador.y - 10), 20, 20)):
            choque_central = True
        
        for enemigo in self.enemigos:
            enemigo_rect = pygame.Rect(int(enemigo.x - 12), int(enemigo.y - 12), 24, 24)
            if obstaculo_central.rect.colliderect(enemigo_rect):
                choque_central = True
                break
        
        if not choque_central:
            self.obstaculos.append(obstaculo_central)

        # Generar obstáculos aleatorios, asegurando que no colisionen con agentes o entre sí.
        intentos_obs = 0
        num_obs = random.randint(2, 4)
        target_obs = num_obs + (1 if not choque_central else 0) # Añade el obstáculo central si no chocó
        
        while len(self.obstaculos) < target_obs and intentos_obs < 100:
            obs_x = random.randint(50, self.ancho_pantalla - 100)
            obs_y = random.randint(50, self.alto_pantalla - 80)
            obs_w = random.randint(30, 60)
            obs_h = random.randint(30, 60)
            nuevo_obs = ObstaculoFuturista(obs_x, obs_y, obs_w, obs_h)

            solapamiento = False
            
            # Verificar colisión con obstáculos existentes
            for obs_exist in self.obstaculos:
                if nuevo_obs.rect.colliderect(obs_exist.rect):
                    solapamiento = True
                    break

            # Verificar colisión con zonas de seguridad alrededor del jugador o enemigos
            zona_segura_j = pygame.Rect(0, 0, 60, 60)
            zona_segura_j.center = (self.ancho_pantalla // 4, self.alto_pantalla // 2)
            zona_segura_e = pygame.Rect(0, 0, 60, 60)
            zona_segura_e.center = (3 * self.ancho_pantalla // 4, self.alto_pantalla // 2)
            
            if (nuevo_obs.rect.colliderect(zona_segura_j) or
                nuevo_obs.rect.colliderect(zona_segura_e)):
                solapamiento = True

            # Verificar colisión con el jugador
            jugador_rect = pygame.Rect(int(self.jugador.x - 10), int(self.jugador.y - 10), 20, 20)
            if nuevo_obs.rect.colliderect(jugador_rect):
                solapamiento = True

            # Verificar colisión con los enemigos
            if not solapamiento:
                for enemigo in self.enemigos:
                    enemigo_rect = pygame.Rect(int(enemigo.x - 12), int(enemigo.y - 12), 24, 24)
                    if nuevo_obs.rect.colliderect(enemigo_rect):
                        solapamiento = True
                        break

            # Mantener distancia mínima con jugador y enemigos para no encerrarlos
            if not solapamiento:
                dist_jugador = math.hypot(
                    (nuevo_obs.rect.centerx - self.jugador.x),
                    (nuevo_obs.rect.centery - self.jugador.y)
                )
                if dist_jugador < 30:
                    solapamiento = True
                
                for enemigo in self.enemigos:
                    dist_enemigo = math.hypot(
                        (nuevo_obs.rect.centerx - enemigo.x),
                        (nuevo_obs.rect.centery - enemigo.y)
                    )
                    if dist_enemigo < 30:
                        solapamiento = True
                        break

            if not solapamiento:
                self.obstaculos.append(nuevo_obs)

            intentos_obs += 1

        self.distancia_anterior = None # Se reinicia para el cálculo de recompensas
        self.pasos = 0 # Contador de pasos del episodio
        self.juego_terminado = False
        self.victoria = False
        self.puntos = 0

        # Inicializa el historial de posiciones del jugador para la predicción de la IA.
        self.algoritmo_ia.historial_jugador.clear()
        for _ in range(3):
            self.algoritmo_ia.historial_jugador.append((self.jugador.x, self.jugador.y))

        observation = self._get_obs()
        info = self._get_info()
        if self.render_mode == "human":
            self._render_frame()
        return observation, info

    def step(self, action):
        """
        Ejecuta un paso del entorno.

        Args:
            action (int): La acción que el jugador (o el agente de entrenamiento) toma.

        Returns:
            tuple: (observation, reward, terminated, truncated, info)
                - observation (np.array): El nuevo estado del entorno.
                - reward (float): La recompensa obtenida en este paso.
                - terminated (bool): True si el episodio ha terminado (victoria/derrota).
                - truncated (bool): True si el episodio ha terminado debido a un límite de tiempo/pasos.
                - info (dict): Información adicional sobre el estado del entorno.
        """
        if self.juego_terminado:
            return self._get_obs(), 0, True, False, self._get_info()
        
        self.pasos += 1

        # Actualiza y gestiona los proyectiles del jugador solo en modo de juego normal.
        if not self.modo_entrenamiento:
            self.jugador.actualizar_proyectiles(self.ancho_pantalla, self.alto_pantalla, self.obstaculos)
            
            # Verifica colisiones entre proyectiles y enemigos.
            for proyectil in self.jugador.proyectiles[:]:
                for enemigo in self.enemigos[:]:
                    if not enemigo.esta_vivo:
                        continue
                    if proyectil.colisiona_con(enemigo):
                        proyectil.activo = False
                        if proyectil in self.jugador.proyectiles:
                            self.jugador.proyectiles.remove(proyectil)
                        
                        # Aplica daño al enemigo y actualiza los puntos.
                        murio = enemigo.recibir_dano(20)
                        if murio:
                            enemigo.esta_vivo = False
                            self.puntos += 100
                        else:
                            self.puntos += 10
                        break

        # Calcula las acciones de los enemigos. Pueden usar la IA inteligente o la acción del agente.
        acciones_enemigos = []
        enemigos_vivos = [e for e in self.enemigos if e.esta_vivo]
        
        if self.usar_ia_inteligente:
            # Los enemigos usan el algoritmo de IA inteligente para calcular su mejor acción.
            for enemigo in enemigos_vivos:
                try:
                    accion_ia = calcular_accion_inteligente(
                        enemigo, self.jugador, self.obstaculos,
                        self.algoritmo_ia, self.modo_ia
                    )
                except Exception as e:
                    print(f"Error en IA inteligente: {e}")
                    accion_ia = action # Fallback a la acción del agente en caso de error
                acciones_enemigos.append(accion_ia)
        else:
            # En modo entrenamiento, todos los enemigos pueden seguir la misma acción para simplificar.
            acciones_enemigos = [action] * len(enemigos_vivos)

        # Mueve a los enemigos vivos según las acciones calculadas.
        movimientos_enemigo = [
            (0, -1), (1, -1), (1, 0), (1, 1),
            (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, 0) # Definición de movimientos en 8 direcciones y quieto
        ]
        
        for idx, enemigo in enumerate(enemigos_vivos):
            if idx < len(acciones_enemigos):
                act = acciones_enemigos[idx]
                dx, dy = movimientos_enemigo[act]
                enemigo.mover(dx, dy, self.obstaculos, enemigos_vivos)

        # Lógica para el movimiento y estado del jugador
        if self.modo_entrenamiento:
            # En modo entrenamiento, la recompensa se basa en la captura del jugador por los enemigos.
            terminado = False
            recompensa = 0
            
            # Verifica si el jugador ha sido "capturado" por algún enemigo.
            for enemigo in enemigos_vivos:
                distancia = math.hypot(enemigo.x - self.jugador.x, enemigo.y - self.jugador.y)
                if distancia < (enemigo.radio + self.jugador.radio):
                    terminado = True
                    self.capturas += 1
                    self.tiempo_captura_promedio.append(self.pasos)
                    recompensa += 300 # Gran recompensa por captura
                    break
            
            # Lógica de recompensa adaptativa: recompensa por acercarse al jugador, penalización por tiempo.
            if not terminado:
                min_dist = min(math.hypot(e.x - self.jugador.x, e.y - self.jugador.y) 
                            for e in enemigos_vivos) if enemigos_vivos else float('inf')
                
                if self.distancia_anterior is not None and enemigos_vivos:
                    dif_dist = self.distancia_anterior - min_dist # Recompensa por disminuir la distancia
                    factor_dist = 1.0 + (200 - min(min_dist, 200)) / 200 # Factor adaptativo para distancias cortas
                    recompensa += dif_dist * factor_dist * 3.0
                
                recompensa -= 0.01 # Penalización por cada paso (para fomentar la eficiencia)
                self.distancia_anterior = min_dist
            
            truncado = self.pasos >= self.max_pasos # El episodio termina si se alcanza el máximo de pasos
            
        else:
            # Modo de juego normal: el jugador maneja el input y el combate es activo.
            self.jugador.manejar_input(self.obstaculos)
            
            # Verifica el contacto enemigo-jugador para quitar vida.
            for enemigo in enemigos_vivos:
                distancia = math.hypot(enemigo.x - self.jugador.x, enemigo.y - self.jugador.y)
                if distancia < (enemigo.radio + self.jugador.radio):
                    murio_jugador = self.jugador.recibir_dano(enemigo.dano_contacto)
                    if murio_jugador:
                        if self.puntos >= 50:
                            self.puntos -= 10
                        self.juego_terminado = True
                        self.victoria = False
                        break
                    elif murio_jugador == False:
                        if self.puntos >= 50:
                            self.puntos -= 10
            
            # Verifica condiciones de victoria/derrota.
            if not enemigos_vivos and not self.juego_terminado:
                self.juego_terminado = True
                self.victoria = True
                self.puntos += 500  # Bonus por victoria
            
            terminado = self.juego_terminado
            recompensa = 0  # Las recompensas en modo juego son los puntos
            truncado = False

        # Construye la observación y la información para el siguiente paso.
        observation = self._get_obs()
        info = self._get_info()

        # Renderiza el frame si el modo es "human".
        if self.render_mode == "human":
            self._render_frame()

        # Generación y gestión de power-ups de salud.
        if time.time() - self.tiempo_ultimo_powerup > self.INTERVALO_POWERUP and not self.modo_entrenamiento:
            for _ in range(5):  # Intenta encontrar un lugar libre para el power-up
                x = random.randint(30, self.ancho_pantalla - 30)
                y = random.randint(30, self.alto_pantalla - 30)
                nuevo = PowerUpSalud(x, y)
                self.INTERVALO_POWERUP = random.randint(7, 12)  # Nuevo intervalo aleatorio para el próximo power-up

                # Verifica que no colisione con obstáculos.
                if any(nuevo.rect().colliderect(obs.rect) for obs in self.obstaculos):
                    continue

                self.powerups_salud.append(nuevo)
                self.tiempo_ultimo_powerup = time.time()
                break
            
        self.powerups_salud = [p for p in self.powerups_salud if p.activo]

        # Actualiza y verifica la interacción del jugador con los power-ups.
        for powerup in self.powerups_salud[:]:
            if self.jugador.vida_actual >= self.jugador.vida_maxima:
                break
            powerup.actualizar()

            distancia = math.hypot(powerup.x - self.jugador.x, powerup.y - self.jugador.y)
            if distancia < (self.jugador.radio + powerup.radio):
                self.jugador.vida_actual = min(self.jugador.vida_maxima, self.jugador.vida_actual + 15)
                self.powerups_salud.remove(powerup)


        # Actualización asíncrona del mapa para generar nuevos obstáculos.
        if time.time() - self.tiempo_ultimo_mapa[0] > self.INTERVALO_MAPA and not hasattr(self, "actualizando_mapa") and not self.modo_entrenamiento:
            self.actualizando_mapa = True
            def set_mapa(nuevo_mapa):
                if nuevo_mapa:
                    # Filtra nuevos obstáculos para evitar colisiones iniciales con agentes.
                    self.obstaculos = generador_mapa.filtrar_obstaculos_sin_colision(nuevo_mapa, [self.jugador] + self.enemigos)
                if hasattr(self, "actualizando_mapa"):
                    delattr(self, "actualizando_mapa")
                self.tiempo_ultimo_mapa[0] = time.time()

            generador_mapa.actualizar_mapa_async(self.ancho_pantalla, self.alto_pantalla, set_mapa)


        return observation, recompensa, terminado, truncado, info


    def _calcular_recompensa_mejorada(self, accion):
        """
        Calcula una recompensa mejorada para el agente de entrenamiento,
        fomentando el acercamiento al jugador y la evitación de obstáculos,
        y penalizando el zigzagueo o la inactividad.
        """
        distancia_actual = min(math.hypot(e.x - self.jugador.x, e.y - self.jugador.y) for e in self.enemigos if e.esta_vivo)
        recompensa = 0

        # Gran recompensa por "capturar" al jugador (distancia muy cercana).
        if distancia_actual < (self.enemigos[0].radio + self.jugador.radio): # Asume que todos los enemigos tienen el mismo radio
            recompensa += 300

        # Recompensa adaptativa por acercarse al jugador.
        if hasattr(self, 'distancia_anterior') and self.distancia_anterior is not None:
            diferencia_distancia = self.distancia_anterior - distancia_actual # Recompensa por la reducción de distancia
            # Un factor de distancia que aumenta la recompensa cuando la distancia es menor,
            # lo que fomenta que el enemigo se acerque aún más una vez cerca.
            factor_distancia = 1.0 + (200 - min(distancia_actual, 200)) / 200
            recompensa += diferencia_distancia * factor_distancia * 3.0

        # Penalización por tiempo, para fomentar la eficiencia en la captura.
        recompensa -= 0.01

        # Penalización por colisiones con obstáculos.
        rect_enemigo = pygame.Rect(
            int(self.enemigos[0].x - self.enemigos[0].radio), # Asume que solo se considera el primer enemigo
            int(self.enemigos[0].y - self.enemigos[0].radio),
            self.enemigos[0].radio * 2, self.enemigos[0].radio * 2
        )
        colision = False
        for obstaculo in self.obstaculos:
            if rect_enemigo.colliderect(obstaculo.rect):
                recompensa -= 5
                colision = True
                break
        if not colision:
            recompensa += 0.5  # Pequeña recompensa por evitar obstáculos

        # Penalización extra por quedarse quieto.
        if accion == 8:
            recompensa -= 1.0

        # Recompensa por eficiencia: mayor recompensa si el enemigo está muy cerca del jugador.
        if distancia_actual < 50:
            recompensa += (50 - distancia_actual) * 0.15

        # Penalización por zigzagueo, para fomentar movimientos más suaves y directos.
        if hasattr(self, 'accion_anterior'):
            if accion != self.accion_anterior and accion != 8: # Si la acción cambia y no es "quieto"
                recompensa -= 0.2
        self.accion_anterior = accion

        self.distancia_anterior = distancia_actual
        return recompensa

    def _render_frame(self):
        """
        Función de renderizado para mostrar el estado actual del juego.
        Incluye un fondo futurista, obstáculos dinámicos, agentes y un HUD.
        """
        if self.pantalla is None:
            pygame.init()
            pygame.display.init()
            self.pantalla = pygame.display.set_mode((self.ancho_pantalla, self.alto_pantalla))
            pygame.display.set_caption("🚀 CYBER PURSUIT")

            if not self.modo_entrenamiento:
                pantalla_bienvenida(self.pantalla, self.ancho_pantalla, self.alto_pantalla)
            self.font = pygame.font.Font(None, 28)
            self.title_font = pygame.font.Font(None, 36)
        if self.clock is None:
            self.clock = pygame.time.Clock()

        # Fondo con gradiente dinámico para un efecto futurista.
        for y in range(self.alto_pantalla):
            base_intensity = 10 + (y / self.alto_pantalla) * 20
            blue_component = int(base_intensity + 10 * math.sin(y * 0.01))
            purple_component = int(base_intensity * 0.7)
            color = (int(base_intensity * 0.3), purple_component, blue_component)
            pygame.draw.line(self.pantalla, color, (0, y), (self.ancho_pantalla, y))

        # Grid futurista con efecto de escaneo.
        grid_intensity = int(40 + 20 * (math.sin(pygame.time.get_ticks() * 0.001) + 1) / 2)
        grid_color = (grid_intensity, grid_intensity, grid_intensity + 20)
        
        for x in range(0, self.ancho_pantalla, 50):
            pygame.draw.line(self.pantalla, grid_color, (x, 0), (x, self.alto_pantalla), 1)
        for y in range(0, self.alto_pantalla, 50):
            pygame.draw.line(self.pantalla, grid_color, (0, y), (self.ancho_pantalla, y), 1)

        # Actualizar y dibujar obstáculos.
        for obstaculo in self.obstaculos:
            if hasattr(obstaculo, 'update'): # Si el obstáculo tiene lógica de actualización, ejecutarla.
                obstaculo.update()
            obstaculo.dibujar(self.pantalla)

        # Dibujar conexiones de IA entre enemigos. Esto visualiza la "coordinación" de los enemigos.
        if len(self.enemigos) > 1:
            for i, enemigo1 in enumerate(self.enemigos):
                if not enemigo1.esta_vivo:
                    continue
                for enemigo2 in self.enemigos[i+1:]:
                    if not enemigo2.esta_vivo:
                        continue
                    dist = math.hypot(enemigo1.x - enemigo2.x, enemigo1.y - enemigo2.y)
                    if dist < 150:  # Dibuja la conexión solo si están cerca
                        alpha = int(50 * (1 - dist / 150)) # Opacidad disminuye con la distancia
                        VisualEffects.draw_particle_trail(
                            self.pantalla, 
                            (enemigo1.x, enemigo1.y), 
                            (enemigo2.x, enemigo2.y),
                            (255, 100, 100),
                            particles=6
                        )

        # Dibujar jugador y enemigos, asegurando que sus posiciones estén dentro de los límites de la pantalla.
        self.jugador.x = max(0, min(self.jugador.x, self.ancho_pantalla))
        self.jugador.y = max(0, min(self.jugador.y, self.alto_pantalla))
        self.jugador.dibujar(self.pantalla)

        for enemigo in self.enemigos:
            if not enemigo.esta_vivo:
                continue
            enemigo.x = max(0, min(enemigo.x, self.ancho_pantalla))
            enemigo.y = max(0, min(enemigo.y, self.alto_pantalla))
            enemigo.dibujar(self.pantalla)

        # Campo de visión del enemigo más cercano, para dar una indicación visual de la detección.
        if self.enemigos:
            enemigos_ordenados = sorted(
                self.enemigos,
                key=lambda e: math.hypot(e.x - self.jugador.x, e.y - self.jugador.y)
            )

            closest_enemy = next((e for e in enemigos_ordenados if e.esta_vivo), None)

            if closest_enemy:
                vision_surface = pygame.Surface((160, 160), pygame.SRCALPHA) # Superficie semitransparente
                pygame.draw.circle(vision_surface, (255, 0, 0, 20), (80, 80), 80) # Círculo interior
                pygame.draw.circle(vision_surface, (255, 100, 100, 40), (80, 80), 80, 2) # Borde del círculo
                self.pantalla.blit(vision_surface, (closest_enemy.x - 80, closest_enemy.y - 80)) # Dibujar en la posición del enemigo


        # Dibuja el HUD (Heads-Up Display) futurista solo en modo de juego normal.
        if not self.modo_entrenamiento:
            self._draw_futuristic_hud()

        # Dibuja los proyectiles del jugador.
        if not self.modo_entrenamiento:
            self.jugador.dibujar_proyectiles(self.pantalla)

        # Dibuja los power-ups de salud.
        for powerup in self.powerups_salud:
            powerup.dibujar(self.pantalla)


        pygame.display.flip() # Actualiza toda la pantalla
        if not self.modo_entrenamiento and self.juego_terminado:
            pantalla_game_over(self.pantalla, self.ancho_pantalla, 
                                     self.alto_pantalla, self.victoria, self.puntos)
    
        # Controla la velocidad de fotogramas del juego.
        self.clock.tick(self.velocidad_juego if not self.modo_entrenamiento else 0)

    def _draw_futuristic_hud(self):
        """
        Dibuja el Heads-Up Display (HUD) con un estilo futurista,
        incluyendo barra de vida, puntos, enemigos restantes, barra de energía
        y un minimapa.
        """
        
        # Barra de vida del jugador.
        vida_porcentaje = self.jugador.vida_actual / self.jugador.vida_maxima if self.jugador.esta_vivo else 0
        vida_bar_width = 180
        vida_bar_height = 11
        padding = 15
        vida_x = padding
        vida_y = self.alto_pantalla - vida_bar_height - padding

        vida_bg = pygame.Rect(vida_x, vida_y, vida_bar_width, vida_bar_height)
        pygame.draw.rect(self.pantalla, (50, 50, 50), vida_bg)

        vida_fill_width = int(vida_bar_width * vida_porcentaje)
        # Cambia el color de la barra de vida según el porcentaje de vida.
        color_vida = (0, 255, 0) if vida_porcentaje > 0.6 else (255, 255, 0) if vida_porcentaje > 0.3 else (255, 0, 0)
        pygame.draw.rect(self.pantalla, color_vida, (vida_x, vida_y, vida_fill_width, vida_bar_height))
        pygame.draw.rect(self.pantalla, (150, 150, 150), vida_bg, 2)
        
        # Puntos en la esquina superior izquierda.
        puntos_text = f"PUNTOS: {self.puntos}"
        puntos_surface = pygame.font.Font(None, 28).render(puntos_text, True, (255, 255, 0))
        self.pantalla.blit(puntos_surface, (15, 15))

        # Enemigos restantes, justo debajo de los puntos.
        enemigos_vivos = sum(1 for e in self.enemigos if e.esta_vivo)
        enemigos_text = f"ENEMIGOS: {enemigos_vivos}"
        enemigos_surface = pygame.font.Font(None, 28).render(enemigos_text, True, (255, 100, 100))
        self.pantalla.blit(enemigos_surface, (15, 45))


        # Barra de energía (stamina) pequeña en la esquina inferior derecha.
        if hasattr(self.jugador, 'boost_energy'):
            bar_width = 120
            bar_height = 12
            padding = 15
            x_pos = self.ancho_pantalla - bar_width - padding
            y_pos = self.alto_pantalla - bar_height - padding

            energy_rect = pygame.Rect(x_pos, y_pos, bar_width, bar_height)
            pygame.draw.rect(self.pantalla, (40, 40, 40), energy_rect)
            fill_width = int(bar_width * max(0, min(self.jugador.boost_energy, 100)) / 100)
            energy_fill = pygame.Rect(x_pos, y_pos, fill_width, bar_height)
            # Cambia el color de la barra de energía según el nivel de energía.
            energy_color = (0, 255, 255) if self.jugador.boost_energy > 50 else (255, 255, 0)
            pygame.draw.rect(self.pantalla, energy_color, energy_fill)
            pygame.draw.rect(self.pantalla, (100, 100, 100), energy_rect, 2)

        # Minimapa en la esquina superior derecha.
        minimap_size = 140
        minimap_rect = pygame.Rect(self.ancho_pantalla - minimap_size - 15, 15, minimap_size, minimap_size)
        minimap_surface = pygame.Surface((minimap_size, minimap_size), pygame.SRCALPHA)

        # La opacidad del fondo del minimapa cambia si el jugador está dentro de su área.
        player_x = max(0, min(self.jugador.x, self.ancho_pantalla))
        player_y = max(0, min(self.jugador.y, self.alto_pantalla))

        # Escala las posiciones del mundo real a las dimensiones del minimapa.
        scale_x = minimap_size / self.ancho_pantalla
        scale_y = minimap_size / self.alto_pantalla

        player_minimap_x = int(player_x * scale_x)
        player_minimap_y = int(player_y * scale_y)

        if (player_minimap_x >= 0 and player_minimap_x <= minimap_size and
            player_minimap_y >= 0 and player_minimap_y <= minimap_size):
            bg_opacity = 80
        else:
            bg_opacity = 150

        pygame.draw.rect(minimap_surface, (0, 0, 0, bg_opacity), (0, 0, minimap_size, minimap_size))
        VisualEffects.draw_tech_border(minimap_surface, pygame.Rect(0, 0, minimap_size, minimap_size), (0, 255, 0), 1)

        # Dibuja obstáculos en el minimapa.
        if hasattr(self, 'obstaculos'):
            for obstaculo in self.obstaculos:
                # Asegura que las coordenadas del obstáculo estén dentro del rango del mapa.
                ox = max(0, min(obstaculo.x, self.ancho_pantalla))
                oy = max(0, min(obstaculo.y, self.alto_pantalla))
                ow = max(1, int(obstaculo.ancho * scale_x))
                oh = max(1, int(obstaculo.alto * scale_y))
                obs_x = int(ox * scale_x)
                obs_y = int(oy * scale_y)
                pygame.draw.rect(minimap_surface, (180, 180, 180), (obs_x, obs_y, ow, oh))

        # Dibuja al jugador en el minimapa.
        pygame.draw.circle(minimap_surface, (0, 150, 255), (player_minimap_x, player_minimap_y), 4)

        # Dibuja a los enemigos en el minimapa.
        for enemigo in self.enemigos:
            if not enemigo.esta_vivo:
                continue
            ex = max(0, min(enemigo.x, self.ancho_pantalla))
            ey = max(0, min(enemigo.y, self.alto_pantalla))
            enemy_x = int(ex * scale_x)
            enemy_y = int(ey * scale_y)
            pygame.draw.circle(minimap_surface, (255, 0, 0), (enemy_x, enemy_y), 3)

        # Dibuja power-ups en el minimapa.
        for powerup in self.powerups_salud:
            if not powerup.activo:
                continue
            px = int(powerup.x * scale_x)
            py = int(powerup.y * scale_y)
            pygame.draw.circle(minimap_surface, (0, 255, 100), (px, py), 3)

        self.pantalla.blit(minimap_surface, minimap_rect.topleft)

        # Etiqueta "RADAR" para el minimapa.
        minimap_label = pygame.font.Font(None, 20).render("RADAR", True, (0, 255, 0))
        self.pantalla.blit(minimap_label, (self.ancho_pantalla - 65, minimap_rect.bottom + 5))


    def cambiar_modo_ia(self, nuevo_modo):
        """
        Cambia el modo de comportamiento de la IA de los enemigos durante el juego.

        Args:
            nuevo_modo (str): El nuevo modo de IA ("hibrido", "predictivo", "campo_potencial", "genetico").
        """
        modos_validos = ["hibrido", "predictivo", "campo_potencial", "genetico"]
        if nuevo_modo in modos_validos:
            self.modo_ia = nuevo_modo
            print(f"Modo IA cambiado a: {nuevo_modo}")
        else:
            print(f"Modo no válido. Opciones: {modos_validos}")

    def render(self):
        """
        Llama a la función interna para renderizar el frame.
        """
        return self._render_frame()

    def close(self):
        """
        Cierra la ventana de Pygame y limpia los recursos.
        """
        if self.pantalla is not None:
            pygame.display.quit()
            pygame.quit()