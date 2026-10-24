/* Minimal Arduino/AVR stand-in so mechy_arm.ino compiles and runs on a PC (tests only). */
#pragma once
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdio.h>

#define F_CPU 16000000UL
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define F(s) (s)
#define _BV(b) (1u << (b))
#define WGM12 3
#define CS10 0
#define OCIE1A 1
#define OCF1A 1
#define ISR(v) extern "C" void v(void)

extern volatile uint8_t PORTA, PORTB, PORTC, PORTD, PORTF, PORTL;
extern volatile uint8_t SREG, TCCR1A, TCCR1B, TIMSK1, TIFR1;
extern volatile uint16_t TCNT1, OCR1A;
void cli();
void sei();
void pinMode(uint8_t pin, uint8_t mode);
void digitalWrite(uint8_t pin, uint8_t v);
int digitalRead(uint8_t pin);
void delayMicroseconds(unsigned int us);
unsigned long millis();
unsigned long micros();

class MockSerial {
 public:
  void begin(unsigned long) {}
  int available();
  int read();
  void print(const char *s);
  void print(char c);
  void print(int v);
  void print(long v);
  void print(unsigned long v);
  void print(double v, int digits = 2);
};
extern MockSerial Serial;
