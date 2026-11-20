# Hub de Juegos

Lanzador de juegos controlado con la mano. Muestra en pantalla los juegos
definidos en `games.json`. Mueve la mano a la izquierda o a la derecha para
elegir un juego y luego haz el gesto de pinza (pulgar con índice) y mantenlo
para iniciarlo. Al salir del juego vuelves al hub.

El hub y ambos juegos comparten un mismo entorno virtual de Python (`.venv`).

## Acerca del proyecto

Proyecto para ferias y exposiciones, desarrollado por estudiantes de Ingeniería
en Informática del Instituto Profesional Santo Tomás, sede Chillán, Chile.

| Juego | Carpeta | Repositorio original |
|-------|---------|----------------------|
| Space Invaders: Hand Control Edition | `games/space-invaders` | [Reas0nt/SpaceInvaderHandControl](https://github.com/Reas0nt/SpaceInvaderHandControl) |
| Flappy Hand | `games/flappy` | [Maikol2305/Flappy-Bird](https://github.com/Maikol2305/Flappy-Bird) |

Los juegos están copiados dentro de este repositorio. Space Invaders se migró de
la API antigua `mp.solutions` a la API Tasks de MediaPipe, para que ambos juegos
compartan `mediapipe==1.2.3`.

## Requisitos

- Python 3.12
- Una cámara web
- `models/hand_landmarker.task` (incluido en el repositorio)

Las dependencias están fijadas en `requirements.txt`:

```text
mediapipe==1.2.3
pygame-ce==2.5.8
pytest==9.2.0
```

`mediapipe` instala también `opencv-contrib-python` y `numpy`. No instales
`opencv-python` ni `pygame` por separado, porque entran en conflicto.

## Instalación

### 1. Clonar el repositorio

```sh
git clone https://github.com/Reas0nt/hand-games-hub.git
cd hand-games-hub
```

### 2. Crear el entorno e instalar dependencias

**Windows** (PowerShell o CMD):

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

**Linux**:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Si usas [uv](https://docs.astral.sh/uv/), también sirve:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

### 3. Ejecutar

- **Windows**: doble clic en `run.bat`, o ejecuta `run.bat` en la terminal.
- **Linux**: `./run.sh` (el archivo ya tiene permiso de ejecución en el
  repositorio; si no, usa `chmod +x run.sh`).

## Controles

| Acción | Gesto | Teclado |
| --- | --- | --- |
| Cambiar selección | Mover la mano a izquierda/derecha | Flechas izquierda / derecha |
| Iniciar el juego seleccionado | Pinza mantenida (unos 0,8 s) | Enter o Espacio |
| Reintentar la cámara | - | F5 |
| Salir del hub | - | Esc |

Al volver de un juego, los gestos se ignoran durante 2 segundos para que una
pinza hecha dentro del juego no inicie otro.

## Variables de entorno

- `HUB_CAMERA_INDEX`: índice de la cámara a usar (por defecto `0`).
- `HUB_WINDOWED=1`: ejecuta en una ventana de 1280x720 en lugar de pantalla
  completa.

## Agregar un juego

Agrega un objeto a la lista `games` en `games.json`:

```json
{
  "id": "my-game",
  "title": "My Game",
  "description": "Short hint shown under the card.",
  "dir": "games/my-game",
  "entry": "main.py",
  "thumbnail": "thumb.png",
  "python": null
}
```

- `dir` es relativo a la carpeta del hub. `entry` es relativo a `dir`.
- `thumbnail` es relativo a la carpeta del juego. Usa `null` u omítelo para
  mostrar una tarjeta de color.
- `python` es opcional. Las rutas relativas se resuelven desde la carpeta del
  hub. Si se omite, el juego se ejecuta con el Python del hub (`.venv`).
- `id` debe ser único.

## Ejecutar los tests

```sh
.venv/bin/python -m pytest -q
```

En Windows: `.venv\Scripts\python -m pytest -q`.

## Solución de problemas

- **"Camera not available - use keyboard"**: otra aplicación puede estar usando
  la cámara. Ciérrala y presiona F5, o define `HUB_CAMERA_INDEX` con otra
  cámara.
- **"Hand model missing"**: falta `models/hand_landmarker.task`. Recupéralo del
  repositorio.
- **`module 'mediapipe' has no attribute 'solutions'`**: código antiguo. Todo el
  proyecto usa la API Tasks de MediaPipe (`mediapipe==1.2.3`). Actualiza el
  archivo y reinstala con `requirements.txt`.
- **Un juego falla justo al iniciar**: el mensaje de error en el hub muestra la
  última línea de la salida de error del juego.
