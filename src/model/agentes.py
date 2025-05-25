import pygame
import math
import random
import sys

sys.path.append("src")

from model.proyectil import Proyectil
from utils.visual_effects import VisualEffects

class Agente:
    """
    Clase base para representar cualquier entidad activa (jugador, enemigo) en el juego.
    Define propiedades comunes como posición, color, vida, y manejo de efectos visuales.
    """
    def __init__(self, x, y, color, radio=10, velocidad=5, agent_type="basic", vida_maxima=100):
        """
        Inicializa un nuevo Agente.

        Args:
            x (int): Coordenada X inicial del agente.
            y (int): Coordenada Y inicial del agente.
            color (tuple): Color RGB del agente (ej. (255, 0, 0) para rojo).
            radio (int, optional): Radio del círculo que representa al agente. Por defecto es 10.
            velocidad (int, optional): Velocidad de movimiento del agente. Por defecto es 5.
            agent_type (str, optional): Tipo de agente ("basic", "player", "enemy"). Por defecto es "basic".
            vida_maxima (int, optional): Puntos de vida máximos del agente. Por defecto es 100.
        """
        self.x = x
        self.y = y
        self.color = color
        self.radio = radio
        self.velocidad = velocidad
        self.agent_type = agent_type
        
        # --- Sistema de vida ---
        self.vida_maxima = vida_maxima
        self.vida_actual = vida_maxima
        self.esta_vivo = True
        self.tiempo_dano = 0  # Marca de tiempo para controlar el efecto visual de daño reciente
        
        # --- Efectos visuales ---
        # `pulse_phase` controla la animación de pulso/brillo del agente.
        self.pulse_phase = random.uniform(0, 2 * math.pi)
        # `trail_positions` guarda las últimas posiciones del agente para dibujar una estela.
        self.trail_positions = [(x, y)] * 5
        # `energy_level` (no usada directamente en `Agente`, pero puede ser útil para subclases)
        self.energy_level = 1.0
        # `shield_rotation` controla la rotación de elementos de escudo (específico para el jugador).
        self.shield_rotation = 0
        
        # Colores calculados para el brillo y el núcleo del agente, basados en el color principal.
        self.glow_color = self._calculate_glow_color()
        self.core_color = self._calculate_core_color()

    def recibir_dano(self, cantidad=20):
        """
        Aplica daño al agente, reduciendo su vida actual.
        Gestiona el estado de "vivo" y un cooldown para el efecto de daño visual.

        Args:
            cantidad (int, optional): La cantidad de daño a aplicar. Por defecto es 20.

        Returns:
            bool or None:
                - True si el agente murió como resultado del daño.
                - False si el agente sobrevivió al daño.
                - None si el agente está en el cooldown de daño (para evitar parpadeo constante).
        """
        if not self.esta_vivo:
            return False  # Si ya está muerto, no se le puede hacer más daño.
        
        # Controla un breve cooldown para el efecto visual de daño.
        if pygame.time.get_ticks() - self.tiempo_dano < 500:
            return None  # Aún en cooldown, no aplicar daño ni efecto visual de nuevo.
        
        self.vida_actual -= cantidad
        self.tiempo_dano = pygame.time.get_ticks()  # Reiniciar el temporizador de daño.
        
        if self.vida_actual <= 0:
            self.vida_actual = 0
            self.esta_vivo = False
            return True  # El agente murió.
        return False  # El agente sobrevivió.

    def update_effects(self):
        """
        Actualiza los parámetros de los efectos visuales del agente para crear animaciones.
        Esto incluye la fase del pulso, la rotación del escudo y la posición de la estela.
        """
        self.pulse_phase += 0.1  # Incrementa la fase para la animación de pulso.
        self.shield_rotation += 2  # Incrementa la rotación del escudo.
        
        # Actualiza las posiciones de la estela: elimina la más antigua y añade la actual.
        self.trail_positions.pop()
        self.trail_positions.insert(0, (self.x, self.y))

    def dibujar(self, superficie):
        """
        Dibuja el agente en la superficie de Pygame, aplicando diversos efectos visuales
        futuristas como estela de movimiento, brillo y efectos de daño.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará el agente.
        """
        if not self.esta_vivo:
            return  # No dibujar si el agente no está vivo.
        
        center = (int(self.x), int(self.y))
        
        # Determina si el agente recibió daño recientemente para aplicar un efecto de parpadeo.
        tiempo_actual = pygame.time.get_ticks()
        dano_reciente = (tiempo_actual - self.tiempo_dano) < 200
        
        # 1. Dibujar estela de movimiento:
        # Itera sobre las posiciones almacenadas en `trail_positions` para dibujar círculos decrecientes
        # en opacidad y tamaño, creando un efecto de rastro.
        for i, pos in enumerate(self.trail_positions[1:]):
            if i < len(self.trail_positions) - 2: # Asegura que no se dibujen puntos de estela demasiado pequeños.
                alpha = int(100 * (1 - i / len(self.trail_positions))) # Opacidad decreciente.
                trail_surface = pygame.Surface((self.radio, self.radio), pygame.SRCALPHA)
                trail_color = (*self.color[:3], alpha) # Usa el color base del agente con opacidad.
                pygame.draw.circle(trail_surface, trail_color, (self.radio//2, self.radio//2), max(1, self.radio - i*2))
                superficie.blit(trail_surface, (int(pos[0] - self.radio//2), int(pos[1] - self.radio//2)))
        
        # 2. Efecto de pulso/brillo externo:
        # La intensidad del brillo varía con `pulse_intensity` para un efecto pulsante.
        pulse_intensity = (math.sin(self.pulse_phase) + 1) / 2
        glow_radius = int(self.radio + 10 + pulse_intensity * 8)
        
        # Si el agente recibió daño recientemente, el brillo parpadea en rojo.
        if dano_reciente and (tiempo_actual // 50) % 2:  # Parpadeo rápido (cada 50ms)
            glow_color = (255, 100, 100)
        else:
            glow_color = self.glow_color
        
        # Dibuja el círculo de brillo utilizando la clase `VisualEffects`.
        VisualEffects.draw_glow_circle(superficie, glow_color, center, self.radio, glow_radius)
        
        # 3. Dibujar según el tipo de agente:
        # Llama a métodos privados específicos para dibujar el cuerpo principal del agente
        # según su `agent_type` (jugador, enemigo o básico).
        if self.agent_type == "player":
            self._draw_player(superficie, center)
        elif self.agent_type == "enemy":
            self._draw_enemy(superficie, center)
            # La barra de vida para enemigos se dibuja solo si es un enemigo.
            self._draw_health_bar(superficie, center)
        else:
            self._draw_basic(superficie, center)
        
        # La barra de vida se dibuja como parte del _draw_enemy, no una llamada global aquí.

    def _draw_health_bar(self, superficie, center):
        """
        Dibuja una barra de vida encima del agente.
        Solo se muestra si la vida actual no es igual a la vida máxima.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará la barra de vida.
            center (tuple): Las coordenadas centrales del agente.
        """
        if self.vida_actual == self.vida_maxima:
            return  # No mostrar la barra si la vida está completa.
        
        bar_width = self.radio * 2 + 10
        bar_height = 4
        # Calcula la posición de la barra de vida para que esté encima del agente.
        bar_x = center[0] - bar_width // 2
        bar_y = center[1] - self.radio - 30
        
        # Fondo de la barra de vida (gris oscuro).
        bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(superficie, (50, 50, 50), bg_rect)
        
        # Parte de la barra que representa la vida actual.
        vida_porcentaje = self.vida_actual / self.vida_maxima
        vida_width = int(bar_width * vida_porcentaje)
        
        if vida_width > 0:
            # El color de la barra de vida cambia según el porcentaje de vida restante.
            if vida_porcentaje > 0.6:
                color_vida = (0, 255, 0)  # Verde
            elif vida_porcentaje > 0.3:
                color_vida = (255, 255, 0) # Amarillo
            else:
                color_vida = (255, 0, 0)   # Rojo
            
            vida_rect = pygame.Rect(bar_x, bar_y, vida_width, bar_height)
            pygame.draw.rect(superficie, color_vida, vida_rect)
        
        # Borde de la barra de vida (gris claro).
        pygame.draw.rect(superficie, (150, 150, 150), bg_rect, 1)
    
    def _calculate_glow_color(self):
        """
        Calcula un color de brillo ligeramente más claro que el color principal del agente.

        Returns:
            tuple: Un color RGB para el brillo.
        """
        r, g, b = self.color[:3]
        return (min(255, r + 50), min(255, g + 50), min(255, b + 50))
    
    def _calculate_core_color(self):
        """
        Calcula un color para el núcleo del agente, más claro que el color principal.

        Returns:
            tuple: Un color RGB para el núcleo.
        """
        r, g, b = self.color[:3]
        return (min(255, r + 100), min(255, g + 100), min(255, b + 100))
    
    def _draw_basic(self, superficie, center):
        """
        Dibuja un agente básico como un círculo con un núcleo.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará.
            center (tuple): Las coordenadas centrales.
        """
        pygame.draw.circle(superficie, self.color, center, self.radio)
        pygame.draw.circle(superficie, self.core_color, center, self.radio - 3)
    
    def _draw_player(self, superficie, center):
        """
        Dibuja el jugador con un diseño futurista que incluye un escudo rotatorio
        y un núcleo hexagonal.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará el jugador.
            center (tuple): Las coordenadas centrales del jugador.
        """
        # Escudo exterior rotatorio: dibuja segmentos de línea que rotan.
        shield_points = []
        for i in range(8):
            angle = (i * math.pi / 4) + math.radians(self.shield_rotation)
            x = center[0] + (self.radio + 8) * math.cos(angle)
            y = center[1] + (self.radio + 8) * math.sin(angle)
            shield_points.append((x, y))
        
        # Dibujar segmentos del escudo, conectando puntos alternos.
        for i in range(0, len(shield_points), 2):
            start = shield_points[i]
            end = shield_points[(i + 1) % len(shield_points)]
            pygame.draw.line(superficie, (0, 150, 255), start, end, 3) # Azul claro para el escudo.
        
        # Núcleo hexagonal: dibuja dos hexágonos concéntricos.
        VisualEffects.draw_hexagon(superficie, (0, 100, 255), center, self.radio - 2) # Hexágono exterior
        VisualEffects.draw_hexagon(superficie, (100, 200, 255), center, self.radio - 5) # Hexágono interior
        
        # Centro brillante del jugador.
        pygame.draw.circle(superficie, (200, 230, 255), center, 3)
        
        # Indicadores de energía: pequeños círculos que rotan alrededor del centro.
        for i in range(4):
            angle = i * math.pi / 2 + self.pulse_phase # Desfase para que roten.
            energy_x = center[0] + 6 * math.cos(angle)
            energy_y = center[1] + 6 * math.sin(angle)
            pygame.draw.circle(superficie, (0, 255, 255), (int(energy_x), int(energy_y)), 2)
    
    def _draw_enemy(self, superficie, center):
        """
        Dibuja un enemigo con un diseño amenazante, similar a un diamante,
        con un núcleo rotatorio y líneas de energía.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará el enemigo.
            center (tuple): Las coordenadas centrales del enemigo.
        """
        # Forma angular/diamante: Define los puntos de un diamante.
        diamond_size = self.radio
        diamond_points = [
            (center[0], center[1] - diamond_size),  # Superior
            (center[0] + diamond_size, center[1]),  # Derecha
            (center[0], center[1] + diamond_size),  # Inferior
            (center[0] - diamond_size, center[1])   # Izquierda
        ]
        
        # Sombra del diamante para dar profundidad.
        shadow_points = [(p[0] + 2, p[1] + 2) for p in diamond_points]
        pygame.draw.polygon(superficie, (100, 0, 0), shadow_points) # Rojo oscuro para la sombra.
        
        # Diamante principal: Relleno y borde.
        pygame.draw.polygon(superficie, self.color, diamond_points) # Color base del enemigo.
        pygame.draw.polygon(superficie, (255, 100, 100), diamond_points, 2) # Borde rojo.
        
        # Núcleo interno rotatorio: Dibuja un triángulo que rota dentro del diamante.
        inner_points = []
        for i in range(3):
            angle = (i * 2 * math.pi / 3) + math.radians(self.shield_rotation * 2) # Más rápido.
            x = center[0] + 5 * math.cos(angle)
            y = center[1] + 5 * math.sin(angle)
            inner_points.append((x, y))
        pygame.draw.polygon(superficie, (255, 0, 0), inner_points) # Rojo brillante.
        
        # Líneas de energía: Pequeñas líneas que emanan del centro.
        for i in range(6):
            angle = i * math.pi / 3 + self.pulse_phase # Rotan con el pulso.
            line_start = (
                center[0] + 4 * math.cos(angle),
                center[1] + 4 * math.sin(angle)
            )
            line_end = (
                center[0] + (self.radio - 2) * math.cos(angle),
                center[1] + (self.radio - 2) * math.sin(angle)
            )
            pygame.draw.line(superficie, (255, 50, 50), line_start, line_end, 1) # Rojo tenue.

    def mover(self, dx, dy, obstaculos=None, otros_agentes=None):
        """
        Mueve el agente en las direcciones especificadas (dx, dy) y gestiona colisiones
        con obstáculos y otros agentes. También actualiza los efectos visuales.

        Args:
            dx (int): Componente de movimiento en el eje X (-1 para izquierda, 1 para derecha, 0 para sin movimiento).
            dy (int): Componente de movimiento en el eje Y (-1 para arriba, 1 para abajo, 0 para sin movimiento).
            obstaculos (list, optional): Lista de objetos ObstaculoFuturista con los que colisionar. Por defecto es None.
            otros_agentes (list, optional): Lista de otros objetos Agente con los que colisionar. Por defecto es None.
        """
        # Calcula el factor de ajuste para movimientos diagonales (para mantener la misma velocidad).
        factor_diag = 0.707 if dx != 0 and dy != 0 else 1.0
        nueva_x = self.x + dx * self.velocidad * factor_diag
        nueva_y = self.y + dy * self.velocidad * factor_diag

        # Crea un rectángulo de colisión para la posición futura del agente.
        rect_futuro = pygame.Rect(
            int(nueva_x - self.radio), int(nueva_y - self.radio),
            self.radio * 2, self.radio * 2
        )

        colision = False
        
        # 1) Verificar colisión contra obstáculos.
        if obstaculos:
            for obst in obstaculos:
                if rect_futuro.colliderect(obst.rect):
                    colision = True
                    break

        # 2) Verificar colisión contra otros agentes (excepto consigo mismo).
        if not colision and otros_agentes:
            for otro in otros_agentes:
                if otro is self:
                    continue # Ignorar la colisión con uno mismo.
                rect_otro = pygame.Rect(
                    int(otro.x - otro.radio), int(otro.y - otro.radio),
                    otro.radio * 2, otro.radio * 2
                )
                if rect_futuro.colliderect(rect_otro):
                    colision = True
                    break

        # Si no hubo colisión, actualiza la posición del agente y sus efectos.
        if not colision:
            # Limita la posición del agente dentro de los límites de la pantalla (800x600, ajustar si es necesario).
            self.x = max(self.radio, min(nueva_x, 800 - self.radio))
            self.y = max(self.radio, min(nueva_y, 600 - self.radio))
            self.update_effects()


class Enemigo(Agente):
    """
    Representa un agente enemigo, heredando de la clase Agente.
    Define características y comportamientos específicos de los enemigos.
    """
    def __init__(self, x, y):
        """
        Inicializa un nuevo Enemigo.

        Args:
            x (int): Coordenada X inicial del enemigo.
            y (int): Coordenada Y inicial del enemigo.
        """
        # Llama al constructor de la clase base (Agente) con parámetros específicos para un enemigo.
        super().__init__(x, y, (255, 50, 50), radio=12, velocidad=3, agent_type="enemy", vida_maxima=60)
        self.scan_angle = 0  # Ángulo para un posible efecto de escaneo.
        self.alert_level = 0 # Nivel de alerta (puede ser usado para IA).
        
        # Daño que causa al jugador por contacto.
        self.dano_contacto = 15
    
    def update_ai_effects(self):
        """
        Actualiza efectos visuales relacionados con la inteligencia artificial del enemigo,
        como un posible escaneo o nivel de alerta.
        """
        self.scan_angle += 5
        # NOTA: `alert_level` no se actualiza aquí, sino que se sugiere calcularlo
        # desde el bucle principal del juego, basándose en la proximidad del jugador.


class Jugador(Agente):
    """
    Representa al jugador, heredando de la clase Agente.
    Incluye funcionalidades específicas del jugador como el sistema de impulso,
    escudo (aunque no implementado en esta versión) y disparo de proyectiles.
    """
    def __init__(self, x, y):
        """
        Inicializa un nuevo Jugador.

        Args:
            x (int): Coordenada X inicial del jugador.
            y (int): Coordenada Y inicial del jugador.
        """
        # Llama al constructor de la clase base (Agente) con parámetros específicos para el jugador.
        super().__init__(x, y, (50, 100, 255), radio=10, velocidad=5, agent_type="player", vida_maxima=100)
        self.boost_energy = 100  # Energía para la habilidad de impulso.
        self.shield_active = False # Estado del escudo (no implementado en esta versión).
        self.boost_locked = False # Bloquea el impulso si la energía llega a 0.
        
        # --- Sistema de disparo ---
        self.proyectiles = []  # Lista para almacenar los proyectiles disparados.
        self.tiempo_ultimo_disparo = 0 # Marca de tiempo del último disparo para controlar la cadencia.
        self.cadencia_disparo = 200  # Milisegundos que deben pasar entre disparos.

    def disparar(self, target_x, target_y):
        """
        Crea un nuevo proyectil y lo añade a la lista de proyectiles del jugador.
        Respeta la cadencia de disparo para evitar disparos demasiado rápidos.

        Args:
            target_x (int): Coordenada X del objetivo al que se dispara.
            target_y (int): Coordenada Y del objetivo al que se dispara.
        """
        tiempo_actual = pygame.time.get_ticks()
        # Verifica si ha pasado suficiente tiempo desde el último disparo.
        if tiempo_actual - self.tiempo_ultimo_disparo >= self.cadencia_disparo:
            proyectil = Proyectil(self.x, self.y, target_x, target_y)
            self.proyectiles.append(proyectil)
            self.tiempo_ultimo_disparo = tiempo_actual

    def actualizar_proyectiles(self, ancho_pantalla, alto_pantalla, obstaculos=[]):
        """
        Actualiza la posición y el estado de todos los proyectiles disparados por el jugador.
        Elimina los proyectiles inactivos (que colisionaron o salieron de la pantalla).

        Args:
            ancho_pantalla (int): Ancho de la ventana de juego.
            alto_pantalla (int): Alto de la ventana de juego.
            obstaculos (list, optional): Lista de obstáculos para la detección de colisiones. Por defecto es una lista vacía.
        """
        # Itera sobre una copia de la lista para poder modificarla durante la iteración.
        for proyectil in self.proyectiles[:]:
            proyectil.update(ancho_pantalla, alto_pantalla, obstaculos)
            if not proyectil.activo:
                self.proyectiles.remove(proyectil) # Elimina el proyectil si ya no está activo.

    def dibujar_proyectiles(self, superficie):
        """
        Dibuja todos los proyectiles activos en la superficie de Pygame.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujarán los proyectiles.
        """
        for proyectil in self.proyectiles:
            proyectil.dibujar(superficie)

    def manejar_input(self, obstaculos=None, otros_agentes=None):
        """
        Procesa la entrada del usuario (teclado y ratón) para mover al jugador
        y disparar proyectiles. También gestiona la lógica del impulso de velocidad.

        Args:
            obstaculos (list, optional): Lista de obstáculos para la detección de colisiones durante el movimiento. Por defecto es None.
            otros_agentes (list, optional): Lista de otros agentes para la detección de colisiones durante el movimiento. Por defecto es None.
        """
        dx = 0
        dy = 0
        keys = pygame.key.get_pressed()
        
        # Disparo con clic del mouse:
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:  # Botón izquierdo del mouse.
            mouse_x, mouse_y = pygame.mouse.get_pos()
            self.disparar(mouse_x, mouse_y)
        
        # Detección de la tecla Shift para el impulso.
        l_shift_pressed = keys[pygame.K_LSHIFT]

        # Movimiento normal basado en las teclas de dirección o WASD.
        if keys[pygame.K_a]:
            dx = -1
        elif keys[pygame.K_d]:
            dx = 1

        if keys[pygame.K_w]:
            dy = -1
        elif keys[pygame.K_s]:
            dy = 1

        # Lógica del impulso (boost):
        if l_shift_pressed and self.boost_energy > 0 and not self.boost_locked:
            speed_multiplier = 1.5
            self.boost_energy = max(0, self.boost_energy - 2) # Consume energía de impulso.
            self.velocidad = 5 * speed_multiplier # Aumenta la velocidad.

            if self.boost_energy == 0:
                self.boost_locked = True # Bloquea el impulso si la energía se agota.
        else:
            if not l_shift_pressed:
                self.boost_locked = False # Desbloquea el impulso si se suelta Shift.
            
            if not self.boost_locked:
                self.boost_energy = min(100, self.boost_energy + 1) # Regenera energía lentamente.
            self.velocidad = 5 # Restablece la velocidad normal.

        # Mueve al jugador aplicando las colisiones.
        self.mover(dx, dy, obstaculos, otros_agentes)