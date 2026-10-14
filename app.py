
import cv2
import mediapipe as mp
import serial
import time
import math

# =========================================
# CONFIGURACOES
# =========================================

PORTA = "COM5"       # Troque pela porta do seu ESP32
BAUDRATE = 115200

TEMPO_ATIVACAO = 1.0  # 1 segundo
LIMITE_DISTANCIA = 0.05

# =========================================
# CONEXAO COM O ESP32
# =========================================

esp32 = serial.Serial(PORTA, BAUDRATE, timeout=1)

# O ESP32 pode reiniciar quando a porta abre
time.sleep(2)

# =========================================
# CONFIGURACAO DO MEDIAPIPE
# =========================================

mp_maos = mp.solutions.hands
mp_desenho = mp.solutions.drawing_utils

maos = mp_maos.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# =========================================
# CAMERA
# =========================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    esp32.close()
    raise RuntimeError("Nao foi possivel abrir a webcam.")

inicio_gesto = None
led_ligado = False
gesto_confirmado = False

try:
    while True:
        sucesso, frame = camera.read()

        if not sucesso:
            break

        # Espelha a imagem como um espelho
        frame = cv2.flip(frame, 1)

        # MediaPipe trabalha com imagem RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado = maos.process(rgb)

        dedos_juntos = False
        distancia = None

        if resultado.multi_hand_landmarks:
            pontos = resultado.multi_hand_landmarks[0]

            # Desenha os pontos e as linhas da mao
            mp_desenho.draw_landmarks(
                frame, pontos, mp_maos.HAND_CONNECTIONS
            )

            # Ponta do polegar e ponta do indicador
            polegar = pontos.landmark[4]
            indicador = pontos.landmark[8]

            # Distancia normalizada entre os dedos
            dx = polegar.x - indicador.x
            dy = polegar.y - indicador.y
            distancia = math.sqrt(dx * dx + dy * dy)

            dedos_juntos = distancia < LIMITE_DISTANCIA

            # Marca as pontas dos dedos
            h, w, _ = frame.shape
            x1, y1 = int(polegar.x * w), int(polegar.y * h)
            x2, y2 = int(indicador.x * w), int(indicador.y * h)

            cv2.circle(frame, (x1, y1), 10, (255, 0, 255), -1)
            cv2.circle(frame, (x2, y2), 10, (255, 0, 255), -1)
            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)

        # =====================================
        # LOGICA DO GESTO DE 1 SEGUNDO
        # =====================================

        if dedos_juntos:
            if inicio_gesto is None:
                inicio_gesto = time.monotonic()

            duracao = time.monotonic() - inicio_gesto

            if duracao >= TEMPO_ATIVACAO and not gesto_confirmado:
                esp32.write(b"1\n")
                led_ligado = True
                gesto_confirmado = True

        else:
            inicio_gesto = None
            gesto_confirmado = False

            if led_ligado:
                esp32.write(b"0\n")
                led_ligado = False

        # =====================================
        # INFORMACOES NA TELA
        # =====================================

        if inicio_gesto is not None:
            duracao = time.monotonic() - inicio_gesto
            texto = f"Segure: {min(duracao, 1.0):.1f}/1.0 s"
        else:
            texto = "Junte polegar e indicador"

        cv2.putText(
            frame, texto, (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
            (0, 255, 0), 2
        )

        status = "LED LIGADO" if led_ligado else "LED DESLIGADO"

        cv2.putText(
            frame, status, (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
            (0, 255, 255), 2
        )

        cv2.imshow("Controle de LED por Gestos", frame)

        # Aperte ESC para encerrar
        if cv2.waitKey(1) & 0xFF == 27:
            break

finally:
    # Garante que o LED seja desligado ao encerrar
    try:
        esp32.write(b"0\n")
    except serial.SerialException:
        pass

    camera.release()
    cv2.destroyAllWindows()
    maos.close()
    esp32.close()
