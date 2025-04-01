#include <WiFi.h>
#include <ArduinoWebsockets.h>

const char* ssid = "CC-Internal_IoT";
const char* password = "SRilbe0i1f-TpFU-";
const char* websocket_server = "ws://10.255.0.12:8765";  // Change to your server's IP

using namespace websockets;
WebsocketsClient client;
DynamicJsonDocument msg(1024);

void onMessageCallback(WebsocketsMessage message) {
    if (deserializeJson(msg, message)) {
      Serial.println("Malformed JSON")
      return;
    }
    Serial.println("Message received: " + '[' + msg["sender"] + ']' + msg["message"]  );
}

void setup() {
    Serial.begin(115200);

    // Connect to WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nConnected to WiFi!");

    // Connect to WebSocket server
    client.onMessage(onMessageCallback);
    client.connect(websocket_server);
}

void loop() {
    if (client.available()) {
        client.poll();  // Process incoming messages
    }

    // Send message every 10 seconds
    static unsigned long lastMessageTime = 0;
    if (millis() - lastMessageTime > 45000) {
        lastMessageTime = millis();
        client.send("{\"sender\": \"ESP32\", \"message\": \"Hello from ESP32!\"}");
    }
}
