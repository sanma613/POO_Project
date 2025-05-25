import heapq
import pygame
import random
from collections import deque
import math

class AlgoritmoPersecucionInteligente:
    """
    Algoritmo híbrido para persecución óptima, combinando:
    - Predicción de movimiento del jugador.
    - A* con heurística predictiva.
    - Campos potenciales para navegación local.
    - Algoritmo genético para optimización de rutas.
    """
    
    def __init__(self, ancho_mapa, alto_mapa, cell_size=15):
        """
        Inicializa el algoritmo con las dimensiones del mapa y el tamaño de celda.

        Args:
            ancho_mapa (int): Ancho del mapa en píxeles.
            alto_mapa (int): Alto del mapa en píxeles.
            cell_size (int): Tamaño de cada celda del grid en píxeles.
        """
        self.ancho_mapa = ancho_mapa
        self.alto_mapa = alto_mapa
        self.cell_size = cell_size
        self.cols = ancho_mapa // cell_size
        self.rows = alto_mapa // cell_size
        
        self.historial_jugador = deque(maxlen=10) # Historial de posiciones del jugador para la predicción de movimiento.
        
        # Algoritmo genético para rutas.
        self.poblacion_rutas = []
        
    def calcular_mejor_accion(self, enemigo, jugador, obstaculos, modo="hibrido"):
        """
        Calcula la mejor acción para el enemigo basada en el modo de algoritmo especificado.

        Args:
            enemigo (object): Objeto que representa al enemigo con atributos x, y.
            jugador (object): Objeto que representa al jugador con atributos x, y.
            obstaculos (list): Lista de objetos de obstáculos con atributos x, y, ancho, alto, rect.
            modo (str): Modo de algoritmo a utilizar ("hibrido", "predictivo", "campo_potencial", "genetico").

        Returns:
            int: Índice de la acción a tomar (0-7 para direcciones, 8 para quieto).
        """
        if modo == "hibrido":
            return self._algoritmo_hibrido(enemigo, jugador, obstaculos)
        elif modo == "predictivo":
            return self._a_star_predictivo(enemigo, jugador, obstaculos)
        elif modo == "campo_potencial":
            return self._campo_potencial(enemigo, jugador, obstaculos)
        elif modo == "genetico":
            return self._algoritmo_genetico(enemigo, jugador, obstaculos)
        else:
            # Por defecto, si el modo no es reconocido, se usa A* predictivo.
            return self._a_star_predictivo(enemigo, jugador, obstaculos)

    def _algoritmo_hibrido(self, enemigo, jugador, obstaculos):
        """
        Implementa un algoritmo híbrido que selecciona la estrategia de persecución
        según la distancia al jugador y la presencia de obstáculos directos.

        - A gran distancia: Algoritmo Genético para encontrar rutas generales.
        - Distancia media: A* predictivo para navegación más precisa y con anticipación.
        - Corta distancia: Campos de potencial si no hay obstáculos directos para un movimiento fluido.
        - Corta distancia con obstáculo directo: Fallback a A* predictivo para sortear el obstáculo.

        Args:
            enemigo (object): Objeto enemigo.
            jugador (object): Objeto jugador.
            obstaculos (list): Lista de objetos obstáculos.

        Returns:
            int: Índice de la acción a tomar.
        """
        self._actualizar_historial_jugador(jugador) # Actualiza el historial de posiciones del jugador para la predicción.

        dx = jugador.x - enemigo.x
        dy = jugador.y - enemigo.y
        distancia = math.hypot(dx, dy)

        # Definición de umbrales de distancia para cambiar de algoritmo.
        UMBRAL_LEJOS_GEN = 300   # Si la distancia es mayor a este umbral, se usa el algoritmo genético.
        UMBRAL_LEJOS = 200       # Si la distancia está entre UMBRAL_LEJOS y UMBRAL_LEJOS_GEN, se usa A* predictivo.
        UMBRAL_CERCA = 80        # Si la distancia es menor a UMBRAL_LEJOS, se evalúa el campo potencial.

        if distancia > UMBRAL_LEJOS_GEN:
            # Caso 1: Jugador muy lejos, se utiliza el algoritmo genético.
            # Se limitan las generaciones para evitar cálculos excesivos y mantener la fluidez.
            return self._algoritmo_genetico(enemigo, jugador, obstaculos, generaciones=3)
        elif distancia > UMBRAL_LEJOS:
            # Caso 2: Jugador a una distancia media, se usa A* predictivo.
            return self._a_star_predictivo(enemigo, jugador, obstaculos)
        else:
            # Caso 3: Jugador cerca. Se verifica si hay un obstáculo directo.
            if not self._hay_obstaculo_directo(enemigo, jugador, obstaculos):
                # Si no hay obstáculo directo, se usa el campo potencial para un movimiento más suave.
                return self._campo_potencial(enemigo, jugador, obstaculos)
            else:
                # Si hay un obstáculo directo a corta distancia, se vuelve a usar A* predictivo
                # para encontrar una ruta alrededor del obstáculo.
                return self._a_star_predictivo(enemigo, jugador, obstaculos)

    def _hay_obstaculo_directo(self, enemigo, jugador, obstaculos):
        """
        Realiza un "raycast" discreto para determinar si hay un obstáculo en la línea recta
        entre el enemigo y el jugador. Esto es crucial para decidir si usar campos de potencial
        (para movimiento fluido en espacio abierto) o A* (para sortear obstáculos).

        Args:
            enemigo (object): Objeto enemigo.
            jugador (object): Objeto jugador.
            obstaculos (list): Lista de objetos obstáculos.

        Returns:
            bool: True si hay un obstáculo directo, False en caso contrario.
        """
        # Calcular el número de pasos para el raycast, basado en la distancia y el tamaño de la celda.
        steps = int(max(abs(enemigo.x - jugador.x), abs(enemigo.y - jugador.y)) // self.cell_size)
        if steps == 0:
            return False

        # Iterar a lo largo de la línea y verificar colisiones con obstáculos.
        for i in range(1, steps + 1):
            t = i / float(steps)
            # Calcular el punto intermedio en la línea.
            x_inter = enemigo.x + (jugador.x - enemigo.x) * t
            y_inter = enemigo.y + (jugador.y - enemigo.y) * t
            # Crear un pequeño rectángulo para representar el punto y verificar colisiones.
            punto = pygame.Rect(int(x_inter), int(y_inter), 2, 2)
            for obs in obstaculos:
                if punto.colliderect(obs.rect):
                    return True
        return False

    
    def _predecir_posicion_jugador(self):
        """
        Predice la próxima posición del jugador basándose en su historial de movimientos.
        Utiliza un promedio ponderado de velocidades, dando más importancia a los movimientos recientes,
        para estimar la trayectoria futura.

        Returns:
            tuple: Coordenadas (x, y) de la posición predicha del jugador.
        """
        # Si no hay suficiente historial, se devuelve la última posición conocida.
        if len(self.historial_jugador) < 3:
            return self.historial_jugador[-1] if self.historial_jugador else (0, 0)
        
        velocidades = []
        # Calcular las velocidades entre puntos consecutivos en el historial.
        for i in range(1, len(self.historial_jugador)):
            prev_pos = self.historial_jugador[i-1]
            curr_pos = self.historial_jugador[i]
            vx = curr_pos[0] - prev_pos[0]
            vy = curr_pos[1] - prev_pos[1]
            velocidades.append((vx, vy))
        
        # Calcular el promedio ponderado de las velocidades. Los movimientos más recientes tienen más peso.
        sum_weights = sum(range(1, len(velocidades)+1))
        vx_pred = sum(vx * (i+1) for i, (vx, vy) in enumerate(velocidades)) / sum_weights
        vy_pred = sum(vy * (i+1) for i, (vx, vy) in enumerate(velocidades)) / sum_weights
        
        pos_actual = self.historial_jugador[-1]
        predicciones = []
        # Proyectar la posición futura del jugador para varios pasos adelante.
        for t in range(1, 6):  # Predecir 5 pasos adelante
            pred_x = pos_actual[0] + vx_pred * t
            pred_y = pos_actual[1] + vy_pred * t
            # Asegurar que las predicciones estén dentro de los límites del mapa.
            pred_x = max(0, min(pred_x, self.ancho_mapa))
            pred_y = max(0, min(pred_y, self.alto_mapa))
            predicciones.append((pred_x, pred_y))
        
        # Devolver una predicción a 3 pasos, que es un buen equilibrio entre reacción y anticipación.
        return predicciones[2] if len(predicciones) > 2 else predicciones[0]
    
    def _a_star_predictivo(self, enemigo, jugador, obstaculos):
        """
        Calcula la ruta utilizando el algoritmo A* con una posición predicha del jugador como objetivo principal.
        Si no se encuentra un camino a la posición predicha, se intenta con la posición actual del jugador.

        Args:
            enemigo (object): Objeto enemigo.
            jugador (object): Objeto jugador.
            obstaculos (list): Lista de objetos obstáculos.

        Returns:
            int: Índice de la acción a tomar.
        """
        pos_predicha = self._predecir_posicion_jugador()
        
        # Crear un grid de navegación con obstáculos inflados para evitar colisiones cercanas.
        grid = self._crear_grid_mejorado(obstaculos)
        
        start = self._pos_a_grid(enemigo.x, enemigo.y)
        
        # Convertir las posiciones predicha y actual del jugador a coordenadas de grid.
        goal_pred = self._pos_a_grid(pos_predicha[0], pos_predicha[1])
        goal_actual = self._pos_a_grid(jugador.x, jugador.y)
        
        # Intentar calcular un camino hacia la posición predicha.
        path = self._a_star_con_heuristica_mejorada(grid, start, goal_pred)
        
        # Si el camino predicho no es válido o muy corto, recalcular hacia la posición actual.
        if not path or len(path) < 2:
            path = self._a_star_con_heuristica_mejorada(grid, start, goal_actual)
        
        # Convertir el primer paso del camino en una acción discreta.
        return self._path_a_accion(path, start)
    
    def _campo_potencial(self, enemigo, jugador, obstaculos):
        """
        Calcula la acción del enemigo usando un enfoque de campos de potencial artificiales.
        El jugador genera una fuerza atractiva, y los obstáculos generan fuerzas repulsivas,
        guiando al enemigo alrededor de ellos de manera fluida.

        Args:
            enemigo (object): Objeto enemigo.
            jugador (object): Objeto jugador.
            obstaculos (list): Lista de objetos obstáculos.

        Returns:
            int: Índice de la acción a tomar.
        """
        # Calcular la fuerza atractiva que jala al enemigo hacia el jugador.
        fx_atractiva = (jugador.x - enemigo.x)
        fy_atractiva = (jugador.y - enemigo.y)
        
        # Normalizar la fuerza atractiva para controlar su magnitud.
        dist_jugador = max(math.sqrt(fx_atractiva**2 + fy_atractiva**2), 1)
        fx_atractiva = fx_atractiva / dist_jugador * 10
        fy_atractiva = fy_atractiva / dist_jugador * 10
        
        # Inicializar las fuerzas repulsivas.
        fx_repulsiva = 0
        fy_repulsiva = 0
        
        radio_evitacion = 25 # Radio dentro del cual los obstáculos ejercen fuerza repulsiva.
        for obstaculo in obstaculos:
            # Calcular la distancia al centro del obstáculo.
            dist_x = enemigo.x - (obstaculo.x + obstaculo.ancho/2)
            dist_y = enemigo.y - (obstaculo.y + obstaculo.alto/2)
            distancia = math.sqrt(dist_x**2 + dist_y**2)
            
            if distancia < 25: # El radio de evitación se define en la línea anterior
                # La fuerza repulsiva es inversamente proporcional al cuadrado de la distancia,
                # lo que significa que es mucho más fuerte cerca del obstáculo.
                factor_repulsion = 500 / max(distancia**2, 1)
                fx_repulsiva += (dist_x / max(distancia, 1)) * factor_repulsion
                fy_repulsiva += (dist_y / max(distancia, 1)) * factor_repulsion
        
        # Sumar todas las fuerzas para obtener la fuerza total resultante.
        fx_total = fx_atractiva + fx_repulsiva
        fy_total = fy_atractiva + fy_repulsiva
        
        # Convertir el vector de fuerza total en una acción de movimiento discreta.
        return self._fuerza_a_accion(fx_total, fy_total)
    
    def _algoritmo_genetico(self, enemigo, jugador, obstaculos, generaciones=5):
        """
        Encuentra una ruta óptima usando un algoritmo genético. Este algoritmo es útil
        para problemas de planificación a largo plazo donde A* podría ser demasiado costoso
        o para encontrar caminos menos directos pero más eficientes en ciertos escenarios.

        Args:
            enemigo (object): Objeto enemigo.
            jugador (object): Objeto jugador.
            obstaculos (list): Lista de objetos obstáculos.
            generaciones (int): Número de generaciones para la evolución de la población.

        Returns:
            int: Índice de la acción a tomar.
        """
        # Si la población de rutas no ha sido inicializada, se crea.
        if not self.poblacion_rutas:
            self._inicializar_poblacion_genetica(enemigo, jugador)
        
        # Se evoluciona la población de rutas a lo largo de varias generaciones.
        for _ in range(generaciones):
            self._evaluar_poblacion(enemigo, jugador, obstaculos)
            self._seleccion_y_reproduccion()
            self._mutacion()
        
        # Una vez terminadas las generaciones, se selecciona la ruta con el mejor fitness.
        mejor_ruta = max(self.poblacion_rutas, key=lambda r: r['fitness'])
        
        # Si la mejor ruta es válida, se devuelve la primera acción de esa ruta.
        if mejor_ruta['path'] and len(mejor_ruta['path']) > 1:
            return self._path_a_accion(mejor_ruta['path'], 
                                     self._pos_a_grid(enemigo.x, enemigo.y))
        
        return 8  # Quieto si no se encuentra una ruta válida.
    
    def _inicializar_poblacion_genetica(self, enemigo, jugador, tamaño_poblacion=20):
        """
        Inicializa la población de rutas para el algoritmo genético.
        Cada "individuo" en la población es una ruta generada aleatoriamente.

        Args:
            enemigo (object): Objeto enemigo.
            jugador (object): Objeto jugador.
            tamaño_poblacion (int): Número de rutas en la población inicial.
        """
        self.poblacion_rutas = []
        start = self._pos_a_grid(enemigo.x, enemigo.y)
        goal = self._pos_a_grid(jugador.x, jugador.y)
        
        for _ in range(tamaño_poblacion):
            # Se genera una ruta aleatoria con un sesgo hacia el objetivo para empezar.
            ruta = self._generar_ruta_aleatoria(start, goal)
            self.poblacion_rutas.append({
                'path': ruta,
                'fitness': 0 # El fitness se calculará posteriormente.
            })
    
    def _generar_ruta_aleatoria(self, start, goal, max_pasos=15):
        """
        Genera una ruta aleatoria. Tiene un sesgo para moverse hacia el objetivo,
        pero también permite movimientos aleatorios para explorar diferentes caminos.

        Args:
            start (tuple): Coordenadas (fila, columna) de inicio.
            goal (tuple): Coordenadas (fila, columna) del objetivo.
            max_pasos (int): Número máximo de pasos para generar la ruta.

        Returns:
            list: Lista de tuplas (fila, columna) que representan la ruta.
        """
        ruta = [start]
        pos_actual = start
        
        for _ in range(max_pasos):
            if pos_actual == goal:
                break
                
            # 70% de probabilidad de moverse en la dirección general del objetivo.
            if random.random() < 0.7:
                dx = 1 if goal[1] > pos_actual[1] else (-1 if goal[1] < pos_actual[1] else 0)
                dy = 1 if goal[0] > pos_actual[0] else (-1 if goal[0] < pos_actual[0] else 0)
            else:
                # 30% de probabilidad de moverse aleatoriamente (exploración).
                dx = random.choice([-1, 0, 1])
                dy = random.choice([-1, 0, 1])
            
            nueva_pos = (pos_actual[0] + dy, pos_actual[1] + dx)
            
            # Se asegura que la nueva posición esté dentro de los límites del grid.
            if (0 <= nueva_pos[0] < self.rows and 
                0 <= nueva_pos[1] < self.cols):
                ruta.append(nueva_pos)
                pos_actual = nueva_pos
        
        return ruta
    
    def _evaluar_poblacion(self, enemigo, jugador, obstaculos):
        """
        Evalúa el "fitness" (idoneidad) de cada ruta en la población genética.
        El fitness se calcula en función de la longitud de la ruta, la proximidad al jugador,
        la colisión con obstáculos y la suavidad de la ruta (menos cambios de dirección).

        Args:
            enemigo (object): Objeto enemigo.
            jugador (object): Objeto jugador.
            obstaculos (list): Lista de objetos obstáculos.
        """
        grid = self._crear_grid_mejorado(obstaculos)
        
        for individuo in self.poblacion_rutas:
            ruta = individuo['path']
            fitness = 0
            
            if not ruta:
                individuo['fitness'] = -1000 # Muy bajo fitness para rutas inválidas.
                continue
            
            # Penalizar por la longitud de la ruta: rutas más cortas son mejores.
            fitness -= len(ruta) * 2
            
            # Recompensar por la proximidad al jugador al final de la ruta.
            if ruta:
                pos_final = ruta[-1]
                pos_final_real = self._grid_a_pos(pos_final[0], pos_final[1])
                dist_final = math.sqrt((pos_final_real[0] - jugador.x)**2 + 
                                     (pos_final_real[1] - jugador.y)**2)
                fitness += max(0, 200 - dist_final) # Mayor recompensa cuanto más cerca esté del jugador.
            
            # Penalizar fuertemente las colisiones con obstáculos.
            for pos in ruta:
                if (0 <= pos[0] < self.rows and 0 <= pos[1] < self.cols and
                    grid[pos[0]][pos[1]] == 1):
                    fitness -= 50
            
            # Recompensar la suavidad de la ruta: menos cambios de dirección son preferibles.
            if len(ruta) > 2:
                cambios_direccion = 0
                for i in range(2, len(ruta)):
                    dir1 = (ruta[i-1][0] - ruta[i-2][0], ruta[i-1][1] - ruta[i-2][1])
                    dir2 = (ruta[i][0] - ruta[i-1][0], ruta[i][1] - ruta[i-1][1])
                    if dir1 != dir2:
                        cambios_direccion += 1
                fitness -= cambios_direccion * 5 # Penalización por cada cambio de dirección.
            
            individuo['fitness'] = fitness
    
    def _seleccion_y_reproduccion(self):
        """
        Realiza la selección de los mejores individuos y la reproducción para crear
        la próxima generación de rutas, manteniendo un elitismo (los mejores individuos
        pasan directamente a la siguiente generación).
        """
        nueva_poblacion = []
        
        # Ordenar la población por fitness de mayor a menor.
        self.poblacion_rutas.sort(key=lambda x: x['fitness'], reverse=True)
        # Elitismo: los 5 mejores individuos pasan directamente a la nueva población.
        nueva_poblacion.extend(self.poblacion_rutas[:5])
        
        # Reproducción: se crean nuevos individuos hasta alcanzar el tamaño de la población.
        while len(nueva_poblacion) < len(self.poblacion_rutas):
            # Selección de padres mediante torneo.
            padre1 = self._seleccion_torneo()
            padre2 = self._seleccion_torneo()
            # Cruce de las rutas de los padres para crear un hijo.
            hijo = self._cruce(padre1, padre2)
            nueva_poblacion.append(hijo)
        
        self.poblacion_rutas = nueva_poblacion
    
    def _seleccion_torneo(self, tamaño_torneo=3):
        """
        Realiza la selección de un individuo (ruta) mediante un torneo.
        Se seleccionan aleatoriamente 'tamaño_torneo' individuos de la población,
        y el que tenga el mejor fitness es el ganador.

        Args:
            tamaño_torneo (int): Número de individuos que participan en el torneo.

        Returns:
            dict: El individuo con el mejor fitness del torneo.
        """
        # Seleccionar candidatos aleatorios para el torneo.
        candidatos = random.sample(self.poblacion_rutas, 
                                 min(tamaño_torneo, len(self.poblacion_rutas)))
        # Devolver el candidato con el fitness más alto.
        return max(candidatos, key=lambda x: x['fitness'])
    
    def _cruce(self, padre1, padre2):
        """
        Realiza el cruce (crossover) entre dos rutas para crear una nueva ruta (hijo).
        Se elige un punto de cruce aleatorio y se combinan las partes de las rutas de los padres.

        Args:
            padre1 (dict): Diccionario que representa al primer padre con su ruta.
            padre2 (dict): Diccionario que representa al segundo padre con su ruta.

        Returns:
            dict: Diccionario que representa al hijo con su nueva ruta.
        """
        if not padre1['path'] or not padre2['path']:
            return {'path': [], 'fitness': 0}
        
        # Elegir un punto de cruce aleatorio.
        punto_cruce = random.randint(1, min(len(padre1['path']), len(padre2['path'])) - 1)
        
        # Combinar la primera parte del padre1 con la segunda parte del padre2.
        nueva_ruta = padre1['path'][:punto_cruce] + padre2['path'][punto_cruce:]
        
        return {'path': nueva_ruta, 'fitness': 0}
    
    def _mutacion(self, tasa_mutacion=0.1):
        """
        Aplica mutaciones a las rutas de la población con una cierta probabilidad.
        Una mutación implica cambiar aleatoriamente un punto en la ruta,
        introduciendo variabilidad y explorando nuevas posibilidades.

        Args:
            tasa_mutacion (float): Probabilidad de que un individuo mute.
        """
        for individuo in self.poblacion_rutas:
            if random.random() < tasa_mutacion and individuo['path']:
                # Seleccionar un índice aleatorio en la ruta para mutar.
                idx = random.randint(0, len(individuo['path']) - 1)
                pos_actual = individuo['path'][idx]
                
                # Generar un movimiento aleatorio para el punto mutado.
                dx = random.choice([-1, 0, 1])
                dy = random.choice([-1, 0, 1])
                nueva_pos = (pos_actual[0] + dy, pos_actual[1] + dx)
                
                # Asegurarse de que la nueva posición esté dentro de los límites del grid.
                if (0 <= nueva_pos[0] < self.rows and 
                    0 <= nueva_pos[1] < self.cols):
                    individuo['path'][idx] = nueva_pos
    
    def _crear_grid_mejorado(self, obstaculos, margen_inflacion=15):
        """
        Crea un grid de navegación donde los obstáculos están "inflados" por un margen.
        Esto crea un área de seguridad alrededor de los obstáculos, haciendo que el pathfinding
        los evite con una mayor holgura, lo que puede resultar en movimientos más suaves y seguros.

        Args:
            obstaculos (list): Lista de objetos obstáculos.
            margen_inflacion (int): Margen en píxeles para inflar los obstáculos.

        Returns:
            list: Grid 2D donde 0 es espacio libre y 1 es obstáculo.
        """
        grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        
        for obstaculo in obstaculos:
            # Crear un rectángulo inflado alrededor de cada obstáculo.
            rect_inflado = pygame.Rect(
                obstaculo.x - margen_inflacion,
                obstaculo.y - margen_inflacion,
                obstaculo.ancho + 2 * margen_inflacion,
                obstaculo.alto + 2 * margen_inflacion
            )
            
            # Marcar todas las celdas del grid que colisionan con el rectángulo inflado como obstáculos.
            for i in range(self.rows):
                for j in range(self.cols):
                    x, y = self._grid_a_pos(i, j)
                    if rect_inflado.collidepoint(x, y):
                        grid[i][j] = 1
        
        return grid
    
    def _a_star_con_heuristica_mejorada(self, grid, start, goal):
        """
        Implementación del algoritmo A* con una heurística combinada (Manhattan + Euclidiana)
        y una penalización adicional por cambios bruscos de dirección. Esto fomenta rutas
        más "suaves" y menos zigzagueantes, lo que puede ser más natural para el movimiento de un agente.

        Args:
            grid (list): Grid 2D de navegación.
            start (tuple): Coordenadas (fila, columna) de inicio.
            goal (tuple): Coordenadas (fila, columna) del objetivo.

        Returns:
            list: Lista de tuplas (fila, columna) que forman el camino más corto.
        """
        # Cola de prioridad para nodos a explorar, ordenada por f_cost (g_cost + h_cost).
        heap = []
        heapq.heappush(heap, (0, start))
        # Diccionario para reconstruir el camino: almacena el predecesor de cada nodo.
        came_from = {start: None}
        # Diccionario para almacenar el costo acumulado desde el inicio hasta cada nodo (g_cost).
        cost_so_far = {start: 0}
        
        while heap:
            # Obtener el nodo con la prioridad más baja (menor f_cost).
            _, current = heapq.heappop(heap)
            
            if current == goal:
                break # Se ha encontrado el objetivo, se sale del bucle.
            
            # Explorar los vecinos (8 direcciones: horizontal, vertical y diagonales).
            for di in [-1, 0, 1]:
                for dj in [-1, 0, 1]:
                    if di == 0 and dj == 0:
                        continue # No se considera el propio nodo.
                    
                    ni, nj = current[0] + di, current[1] + dj
                    
                    # Verificar si el vecino está dentro de los límites del grid y no es un obstáculo.
                    if (0 <= ni < self.rows and 0 <= nj < self.cols and 
                        grid[ni][nj] == 0):
                        
                        # Costo de movimiento: 1 para movimientos ortogonales, 1.414 para diagonales.
                        move_cost = 1.414 if di != 0 and dj != 0 else 1.0
                        
                        # Penalización por cambios de dirección: si el movimiento actual cambia bruscamente
                        # con respecto al movimiento anterior, se añade un pequeño costo.
                        if current in came_from and came_from[current]:
                            prev = came_from[current]
                            prev_dir = (current[0] - prev[0], current[1] - prev[1])
                            curr_dir = (di, dj)
                            if prev_dir != curr_dir:
                                move_cost += 0.1
                        
                        new_cost = cost_so_far[current] + move_cost
                        neighbor = (ni, nj)
                        
                        # Si se encuentra un camino más corto al vecino o es la primera vez que se visita.
                        if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                            cost_so_far[neighbor] = new_cost
                            
                            # Heurística mejorada: combinación de distancia Manhattan (más rápida)
                            # y Euclidiana (más precisa) para una estimación de costo restante más efectiva.
                            h_manhattan = abs(goal[0] - ni) + abs(goal[1] - nj)
                            h_euclidiana = math.sqrt((goal[0] - ni)**2 + (goal[1] - nj)**2)
                            heuristica = 0.7 * h_euclidiana + 0.3 * h_manhattan
                            
                            # Calcular la prioridad (f_cost) para la cola de prioridad.
                            priority = new_cost + heuristica
                            heapq.heappush(heap, (priority, neighbor))
                            came_from[neighbor] = current # Registrar el predecesor para reconstruir el camino.
        
        # Reconstruir el camino desde el objetivo hasta el inicio, siguiendo los predecesores.
        if goal not in came_from:
            return [] # No se encontró un camino al objetivo.
        
        path = []
        node = goal
        while node is not None:
            path.append(node)
            node = came_from.get(node)
        path.reverse() # Invertir el camino para que vaya de inicio a fin.
        
        return path
    
    def _actualizar_historial_jugador(self, jugador):
        """
        Actualiza el historial de posiciones del jugador. Es una lista circular (deque)
        que mantiene solo las últimas 'maxlen' posiciones para la predicción.

        Args:
            jugador (object): Objeto jugador.
        """
        self.historial_jugador.append((jugador.x, jugador.y))
    
    def _pos_a_grid(self, x, y):
        """
        Convierte una posición de píxeles (coordenadas del mundo) a coordenadas de celda en el grid.

        Args:
            x (int): Coordenada X en píxeles.
            y (int): Coordenada Y en píxeles.

        Returns:
            tuple: Coordenadas (fila, columna) en el grid.
        """
        return int(y // self.cell_size), int(x // self.cell_size)
    
    def _grid_a_pos(self, i, j):
        """
        Convierte coordenadas de celda del grid (fila, columna) a una posición central en píxeles.
        Útil para dibujar o para cálculos que requieren coordenadas del mundo.

        Args:
            i (int): Índice de fila en el grid.
            j (int): Índice de columna en el grid.

        Returns:
            tuple: Coordenadas (x, y) en píxeles.
        """
        return j * self.cell_size + self.cell_size // 2, i * self.cell_size + self.cell_size // 2
    
    def _fuerza_a_accion(self, fx, fy):
        """
        Convierte un vector de fuerza (fx, fy) resultante del campo de potencial a una acción
        discreta de movimiento (por ejemplo, arriba, abajo, diagonal, quieto).
        Normaliza las fuerzas y las mapea a una de las 9 posibles direcciones.

        Args:
            fx (float): Componente X de la fuerza.
            fy (float): Componente Y de la fuerza.

        Returns:
            int: Índice de la acción a tomar.
        """
        magnitud = math.sqrt(fx**2 + fy**2)
        if magnitud < 0.1:
            return 8  # Si la magnitud es muy pequeña, significa que la fuerza es insignificante, quedarse quieto.
        
        # Normalizar las fuerzas para obtener la dirección.
        fx_norm = fx / magnitud
        fy_norm = fy / magnitud
        
        # Determinar el componente de movimiento en X (horizontal).
        if fx_norm > 0.5:
            dx = 1
        elif fx_norm < -0.5:
            dx = -1
        else:
            dx = 0
            
        # Determinar el componente de movimiento en Y (vertical).
        if fy_norm > 0.5:
            dy = 1
        elif fy_norm < -0.5:
            dy = -1
        else:
            dy = 0
        
        # Mapeo de vectores de dirección (dx, dy) a un índice de acción.
        movimientos = [
            (0, -1), (1, -1), (1, 0), (1, 1),    # 0: Arriba, 1: Arriba-Derecha, 2: Derecha, 3: Abajo-Derecha
            (0, 1), (-1, 1), (-1, 0), (-1, -1),  # 4: Abajo, 5: Abajo-Izquierda, 6: Izquierda, 7: Arriba-Izquierda
            (0, 0)                               # 8: Quieto
        ]
        
        try:
            return movimientos.index((dx, dy))
        except ValueError:
            return 8  # Si no se encuentra una dirección exacta, el enemigo se queda quieto.
    
    def _path_a_accion(self, path, start):
        """
        Convierte una ruta (lista de celdas en el grid) en la próxima acción discreta a tomar.
        Esencialmente, calcula la dirección desde la posición actual del enemigo hacia el
        siguiente punto en el camino calculado.

        Args:
            path (list): Lista de tuplas (fila, columna) que forman la ruta.
            start (tuple): Coordenadas (fila, columna) de la posición actual del enemigo.

        Returns:
            int: Índice de la acción a tomar.
        """
        if not path or len(path) < 2:
            return 8 # Si no hay camino o el camino es solo la posición actual, quedarse quieto.
        
        # El siguiente punto en el camino.
        next_pos = path[1]
        
        # Calcular el cambio en fila y columna.
        di = next_pos[0] - start[0]
        dj = next_pos[1] - start[1]
        
        # Normalizar los cambios a -1, 0, o 1 para mapear a las 8 direcciones o quieto.
        di = max(-1, min(1, di))
        dj = max(-1, min(1, dj))
        
        # Mapeo de vectores de dirección (dj, di) a un índice de acción.
        movimientos = [
            (0, -1), (1, -1), (1, 0), (1, 1),
            (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, 0)
        ]
        
        try:
            # Notar que aquí el mapeo es (dj, di) porque 'movimientos' está definido
            # con el cambio en X (horizontal) primero y luego Y (vertical).
            return movimientos.index((dj, di))
        except ValueError:
            return 8 # Si la dirección no coincide con ninguna acción, el enemigo se queda quieto.

def calcular_accion_inteligente(enemigo, jugador, obstaculos, algoritmo_ia, modo="hibrido"):
    """
    Función principal para calcular la mejor acción del enemigo.
    Actúa como una interfaz para el AlgoritmoPersecucionInteligente.
    
    Args:
        enemigo (object): Objeto que representa al enemigo.
        jugador (object): Objeto que representa al jugador.
        obstaculos (list): Lista de objetos de obstáculos.
        algoritmo_ia (AlgoritmoPersecucionInteligente): Instancia del algoritmo IA.
        modo (str): Modo de algoritmo a utilizar ("hibrido", "predictivo", "campo_potencial", "genetico").

    Returns:
        int: Índice de la acción a tomar (0-7 para direcciones, 8 para quieto).
    """
    return algoritmo_ia.calcular_mejor_accion(enemigo, jugador, obstaculos, modo)