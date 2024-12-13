#include <PulseSensorPlayground.h>
#include <DHT.h>
#include <DHT_U.h>
#define DHTPIN 2
#define DHTTYPE DHT22

DHT dht(DHTPIN, DHTTYPE);


int PulseSensorPurplePin = 0;  // Pulse Sensor PURPLE WIRE connected to ANALOG PIN 0
int Signal;                    // holds the incoming raw data. Signal value can range from 0-1024
int Threshold = 570;           // Determine which Signal to "count as a beat", and which to ignore.
int beforeaverage = 0;   
int sum = 0;                  // Initialize sum to 0
int fix2 = 0;                 // Initialize fix2 to 0
int sa = 0;                   // Initialize sa to 0


void setup() {
  Serial.begin(9600);  
  dht.begin();
}

void loop() {
  int ave, fix;

  int h = dht.readHumidity();

  sum++; // Increment sum each time loop is executed

  Signal = analogRead(PulseSensorPurplePin);  
  fix = Signal / 4;  // Scale down the signal

  Serial.print(fix);
  Serial.print(",");
  Serial.println(h);
  Serial.flush();
  delay(2000); // Small delay between readings
}
