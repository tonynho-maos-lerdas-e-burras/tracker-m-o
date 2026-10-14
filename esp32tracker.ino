const int LED = 27;

void setup() {
  pinMode(LED, OUTPUT);
  digitalWrite(LED, LOW);

  Serial.begin(115200);
  Serial.println("ESP32 pronto!");
}

void loop() {
  if (Serial.available() > 0) {
    char comando = Serial.read();

    if (comando == '1') {
      digitalWrite(LED, HIGH);
      Serial.println("LED LIGADO");
    }

    if (comando == '0') {
      digitalWrite(LED, LOW);
      Serial.println("LED DESLIGADO");
    }
  }
}