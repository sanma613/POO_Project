import requests
import pygame
import json
import re
import random
import sys
import threading

sys.path.append("src")

# Importación de la clase ObstaculoFuturista, necesaria para crear los obstáculos.
from model.entorno import ObstaculoFuturista

# Clave API para el servicio de generación de mapas.
API_KEY = "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"

class GeneradorDeMapas:
    """
    Clase encargada de generar dinámicamente el diseño de mapas para el juego,
    incluyendo la posición y el tamaño de los obstáculos. Utiliza una API externa
    para obtener diseños de mapas complejos y permite la generación local de obstáculos
    simples con manejo de colisiones.
    """
    def __init__(self, api_key=API_KEY, modelo_api="deepseek/deepseek-prover-v2:free"):
        """
        Inicializa el generador de mapas.

        Args:
            api_key (str, optional): La clave API para autenticarse con el servicio de generación de mapas.
                                     Por defecto es la clave definida globalmente.
            modelo_api (str, optional): El modelo de lenguaje a utilizar en la API.
                                        Por defecto es "deepseek/deepseek-prover-v2:free".
        """
        self.api_key = api_key
        self.modelo_api = modelo_api

    def obtener_mapa_aleatorio(self, ancho, alto, num_obstaculos=5, radio_jugador=10, radio_enemigo=12):
        """
        Obtiene un conjunto de obstáculos para el mapa utilizando una API externa.
        El prompt está diseñado para generar un diseño de nivel estratégico con
        diferentes tamaños de pasajes para el jugador y los enemigos.

        Args:
            ancho (int): El ancho del mapa de juego en píxeles.
            alto (int): El alto del mapa de juego en píxeles.
            num_obstaculos (int, optional): El número exacto de obstáculos a generar. Por defecto es 5.
            radio_jugador (int, optional): El radio del jugador, usado para definir el tamaño de los pasajes. Por defecto es 10.
            radio_enemigo (int, optional): El radio de los enemigos, usado para definir el tamaño de los pasajes. Por defecto es 12.

        Returns:
            list: Una lista de diccionarios, donde cada diccionario representa un obstáculo
                  con las claves "x", "y", "ancho" y "alto". Retorna una lista vacía si falla la API.
        """
        if not self.api_key:
            print("Advertencia: No se ha proporcionado una clave API. No se generará el mapa.")
            return []

        # Construcción del prompt para la API, incluyendo requisitos específicos del diseño de nivel.
        # Es crucial que el formato de salida sea estrictamente JSON para facilitar el parseo.
        prompt = (
            f"Generate exactly {num_obstaculos} rectangular obstacles for a {ancho}x{alto} pixel video game map. "
            f"MANDATORY REQUIREMENTS:\n"
            f"- ALWAYS include one central obstacle near the map center\n"
            f"- Create a challenging but playable level with STRATEGIC GAP SIZES:\n"
            f"  * Player radius: {radio_jugador}px, Enemy radius: {radio_enemigo}px\n"
            f"  * Create some narrow gaps ({radio_enemigo * 2 + 5}-{radio_jugador * 2 - 5}px) where ONLY enemies can fit through\n"
            f"  * Create wider passages ({radio_jugador * 2 + 10}px+) where both player and enemies can move\n"
            f"- Use tight spaces as enemy escape routes and tactical advantages\n"
            f"- Vary obstacle sizes: small (30-80px), medium (80-150px), large (150-300px)\n"
            f"- Position obstacles to create chokepoints and enemy-only shortcuts\n"
            f"- Keep all obstacles within bounds (0,0) to ({ancho},{alto})\n"
            f"- Prevent complete obstacle overlap but allow strategic narrow passages\n"
            f"- Leave spawn areas clear near corners\n\n"
            f"TACTICAL DESIGN GOAL: Create cat-and-mouse gameplay where smaller enemies can escape through gaps the larger player cannot follow.\n\n"
            f"OUTPUT FORMAT:\n"
            f"CRITICAL: Respond with ONLY a valid JSON array. No explanations, no markdown, no extra text.\n"
            f"Example format: [{{\"x\":100,\"y\":100,\"ancho\":50,\"alto\":150}}]"
        )

        try:
            # Realiza la solicitud POST a la API de OpenRouter.
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}", # Autenticación con la clave API.
                    "Content-Type": "application/json" # Indica que el cuerpo de la solicitud es JSON.
                },
                json={
                    "model": self.modelo_api, # Especifica el modelo de IA a usar.
                    "messages": [{"role": "user", "content": prompt}], # El prompt enviado a la IA.
                    "max_tokens": 200, # Limita la longitud de la respuesta para evitar respuestas muy largas.
                    "temperature": 0.7 # Controla la creatividad de la respuesta (0.0 a 1.0).
                }
            )
            response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx).
            
            # Intenta parsear el contenido de la respuesta JSON.
            content = response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            # Captura errores de red o HTTP.
            print(f"[MAPA API FALLÓ] Usando fallback local: {e}")
            return [{"x": o.x, "y": o.y, "ancho": o.ancho, "alto": o.alto} for o in self.generar_obstaculos_sin_colision(ancho, alto, [], num_obstaculos)]
        except KeyError as e:
            # Captura errores si la estructura JSON no es la esperada.
            print(f"Error al parsear la respuesta JSON de la API (clave faltante): {e}")
            print(f"Contenido completo de la respuesta: {response.text}")
            return []
        except Exception as e:
            # Captura cualquier otra excepción inesperada.
            print(f"Error inesperado al obtener el mapa: {e}")
            return []

        try:
            # Intenta cargar el contenido como JSON directamente.
            return json.loads(content)
        except json.JSONDecodeError:
            # Si el contenido no es JSON puro, intenta extraer el JSON con una regex.
            print("El contenido de la API no es JSON puro. Intentando extraer JSON con regex...")
            json_str = re.search(r"\[.*\]", content, re.DOTALL)
            if json_str:
                try:
                    return json.loads(json_str.group(0))
                except json.JSONDecodeError as e:
                    print(f"Error al parsear JSON extraído con regex: {e}")
            print("No se pudo extraer un JSON válido de la respuesta de la API.")
            return []

    def generar_obstaculos_sin_colision(self, ancho, alto, entidades, num_obstaculos=4, max_intentos=100):
        """
        Genera un número de obstáculos rectangulares de forma aleatoria,
        asegurándose de que no colisionen entre sí ni con las entidades iniciales (jugador, enemigos).
        Este método es una alternativa a la generación por API para casos más simples o como fallback.

        Args:
            ancho (int): El ancho del mapa.
            alto (int): El alto del mapa.
            entidades (list): Una lista de objetos que ya están en el mapa (ej. Jugador, Enemigo)
                              para evitar generar obstáculos encima de ellos.
            num_obstaculos (int, optional): El número deseado de obstáculos a generar. Por defecto es 4.
            max_intentos (int, optional): El número máximo de intentos para colocar un obstáculo
                                          antes de desistir. Por defecto es 100.

        Returns:
            list: Una lista de objetos `ObstaculoFuturista` generados.
        """
        obstaculos = []
        intentos = 0
        while len(obstaculos) < num_obstaculos and intentos < max_intentos:
            # Genera dimensiones y posición aleatorias para el nuevo obstáculo.
            w = random.randint(30, 100)
            h = random.randint(30, 100)
            x = random.randint(0, ancho - w)
            y = random.randint(0, alto - h)
            nuevo_rect = pygame.Rect(x, y, w, h)

            # Verifica colisión con entidades existentes.
            colision_con_entidades = False
            for entidad in entidades:
                entidad_rect = pygame.Rect(
                    int(entidad.x - entidad.radio), int(entidad.y - entidad.radio),
                    entidad.radio * 2, entidad.radio * 2
                )
                if nuevo_rect.colliderect(entidad_rect):
                    colision_con_entidades = True
                    break
            
            if colision_con_entidades:
                intentos += 1
                continue # Reintentar si colisiona con una entidad.

            # Verifica colisión con otros obstáculos ya generados.
            colision_con_obstaculos = False
            for obs in obstaculos:
                if nuevo_rect.colliderect(obs.rect):
                    colision_con_obstaculos = True
                    break
            
            if colision_con_obstaculos:
                intentos += 1
                continue # Reintentar si colisiona con otro obstáculo.
            
            # Si no hay colisiones, añade el nuevo obstáculo a la lista.
            obstaculos.append(ObstaculoFuturista(x, y, w, h))
            intentos += 1 # Incrementa el intento incluso si tiene éxito para evitar bucles infinitos.
        return obstaculos

    def filtrar_obstaculos_sin_colision(self, mapa_json, entidades):
        """
        Filtra una lista de obstáculos (en formato JSON) para asegurarse de que
        no colisionen con las entidades iniciales del juego. Esto es útil si la API
        genera obstáculos que se superponen con las posiciones de inicio del jugador o enemigos.

        Args:
            mapa_json (list): Una lista de diccionarios, cada uno representando un obstáculo
                              con "x", "y", "ancho" y "alto".
            entidades (list): Una lista de objetos que ya están en el mapa (ej. Jugador, Enemigo)
                              para evitar superposición.

        Returns:
            list: Una lista de objetos `ObstaculoFuturista` que no colisionan con las entidades.
        """
        obstaculos_filtrados = []
        for o in mapa_json:
            # Crea un rectángulo de Pygame a partir de los datos del obstáculo.
            rect = pygame.Rect(o["x"], o["y"], o["ancho"], o["alto"])
            
            # Verifica si este obstáculo colisiona con alguna de las entidades.
            colisiona = False
            for e in entidades:
                entidad_rect = pygame.Rect(
                    int(e.x - e.radio), int(e.y - e.radio),
                    e.radio * 2, e.radio * 2
                )
                if rect.colliderect(entidad_rect):
                    colisiona = True
                    break # Si colisiona con una entidad, no lo añadimos y pasamos al siguiente obstáculo.
            
            if not colisiona:
                # Si no colisiona con ninguna entidad, crea el objeto ObstaculoFuturista y añádelo.
                obstaculos_filtrados.append(ObstaculoFuturista(o["x"], o["y"], o["ancho"], o["alto"]))
        return obstaculos_filtrados
    
    def actualizar_mapa_async(self, ancho, alto, callback):
        """
        Inicia la generación de un nuevo mapa aleatorio en un hilo separado.
        Cuando el mapa es generado, llama a la función de 'callback' proporcionada
        con los datos del nuevo mapa. Esto evita que la interfaz de usuario se congele
        mientras se espera la respuesta de la API.

        Args:
            ancho (int): El ancho del mapa.
            alto (int): El alto del mapa.
            callback (function): Una función que será llamada con el nuevo mapa generado
                                 como argumento (ej. `callback(nuevo_mapa_data)`).
        """
        def worker():
            """
            Función interna que ejecuta la lógica de generación del mapa y llama al callback.
            Se ejecuta en un hilo separado.
            """
            nuevo_mapa = self.obtener_mapa_aleatorio(ancho, alto)
            callback(nuevo_mapa) # Llama a la función de retorno con el resultado.
        
        # Crea y arranca un nuevo hilo. `daemon=True` asegura que el hilo se cierre
        # automáticamente cuando el programa principal termine.
        threading.Thread(target=worker, daemon=True).start()