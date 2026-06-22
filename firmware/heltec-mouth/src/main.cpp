#include <Arduino.h>
#include <ArduinoJson.h>
#include <U8g2lib.h>
#include <Wire.h>
#include "config.h"

U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R0, KOALA_OLED_RST, KOALA_OLED_SCL, KOALA_OLED_SDA);

static bool active=false;
static char stateName[18]="idle";
static char lineText[64]="";
static uint8_t frameNo=0;
static uint32_t untilMs=0,lastMs=0;

static bool eq(const char*a,const char*b){return a&&b&&!strcasecmp(a,b);} 

static void header(){
  oled.setFont(u8g2_font_5x7_tr);
  oled.drawFrame(0,0,128,64);
  oled.drawStr(5,9,"KILLERKOALA");
  oled.drawStr(82,9,stateName);
  for(int x=4;x<124;x+=8)oled.drawVLine(x,13,(x%24==4)?5:3);
}

static void drawLineText(){
  oled.setFont(u8g2_font_5x7_tr);
  char clipped[23];
  snprintf(clipped,sizeof(clipped),"%s",lineText[0]?lineText:"AI koala mouth");
  oled.drawStr(5,59,clipped);
}

static void drawMouthShape(int cx,int cy){
  if(eq(stateName,"speaking")){
    int open=5+(frameNo%8);
    int width=44+((frameNo%3)*4);
    oled.drawRBox(cx-width/2,cy-open,width,open*2,6);
    oled.setDrawColor(0); oled.drawHLine(cx-width/2+6,cy,width-12); oled.setDrawColor(1);
  }else if(eq(stateName,"wake")||eq(stateName,"listening")){
    int nudge=(frameNo%6)-3;
    oled.drawHLine(cx-26,cy+nudge,52);
    oled.drawPixel(cx-31,cy+nudge); oled.drawPixel(cx+31,cy+nudge);
  }else if(eq(stateName,"thinking")){
    for(int x=-32;x<=32;x+=10)oled.drawDisc(cx+x,cy+(((x/10+frameNo)%2)?3:-3),2);
  }else if(eq(stateName,"action")){
    int sweep=(frameNo%16)-8;
    oled.drawHLine(cx-34,cy,68);
    for(int x=-28;x<=28;x+=14)oled.drawVLine(cx+x+sweep/3,cy-7,14);
  }else if(eq(stateName,"success")){
    int lift=(frameNo%6<3)?0:2;
    oled.drawLine(cx-28,cy-lift,cx-12,cy+7-lift); oled.drawLine(cx-12,cy+7-lift,cx+12,cy+7-lift); oled.drawLine(cx+12,cy+7-lift,cx+28,cy-lift);
  }else if(eq(stateName,"error")||eq(stateName,"blocked")){
    int dip=(frameNo%6<3)?0:2;
    oled.drawLine(cx-28,cy+6+dip,cx-12,cy-1+dip); oled.drawLine(cx-12,cy-1+dip,cx+12,cy-1+dip); oled.drawLine(cx+12,cy-1+dip,cx+28,cy+6+dip);
  }else{
    oled.drawHLine(cx-24,cy,48);
  }
}

static void drawSnout(){
  int cx=64, cy=35;
  int bob=(eq(stateName,"speaking")||eq(stateName,"wake"))?((frameNo%6)-3)/2:0;
  oled.drawRFrame(cx-50,cy-20+bob,100,36,12);
  oled.drawRFrame(cx-16,cy-22+bob,32,13,6);
  oled.drawBox(cx-4,cy-10+bob,8,3);
  oled.drawRFrame(cx-38,cy-8+bob,76,20,6);
  drawMouthShape(cx,cy+bob);
}

static void drawFace(){
  oled.clearBuffer();
  header();
  drawSnout();
  drawLineText();
  oled.sendBuffer();
}

static bool isActive(){
  if(!active)return false;
  if((int32_t)(millis()-untilMs)>0){active=false;return false;}
  return true;
}

static void showFace(const char*state,const char*msg,int duration){
  snprintf(stateName,sizeof(stateName),"%s",state&&state[0]?state:"listening");
  snprintf(lineText,sizeof(lineText),"%s",msg?msg:"");
  active=true; frameNo=0; lastMs=0; untilMs=millis()+(uint32_t)(duration>0?duration:KOALA_FACE_DEFAULT_DURATION_MS);
  drawFace();
}

static void sendAck(const char*state){
  StaticJsonDocument<160> ack; ack["type"]="killerkoala_oled_ack"; ack["device"]="heltec-oled"; ack["state"]=state; ack["active"]=isActive(); serializeJson(ack,Serial); Serial.println();
}

static void handleJson(const String&line){
  StaticJsonDocument<768> doc; if(deserializeJson(doc,line))return;
  const char*type=doc["type"]|"";
  if(!strcmp(type,"killerkoala_face")||!strcmp(type,"ai_face")){
    bool enabled=doc["enabled"]|true;
    const char*state=doc["state"]|"listening";
    if(!enabled){active=false;oled.clearBuffer();oled.sendBuffer();sendAck("hidden");return;}
    showFace(state,doc["message"]|"",doc["duration_ms"]|KOALA_FACE_DEFAULT_DURATION_MS);
    sendAck(state);
  }else if(!strcmp(type,"screen")){
    active=false; oled.clearBuffer(); oled.sendBuffer(); sendAck("suppressed_for_app");
  }
}

static void pollSerial(){
  static String line;
  while(Serial.available()){
    char ch=(char)Serial.read();
    if(ch=='\n'){handleJson(line);line="";} else if(ch!='\r'){line+=ch;if(line.length()>1024)line="";}
  }
}

static void tick(){
  if(!isActive())return;
  uint32_t now=millis(); if(now-lastMs<90)return;
  lastMs=now; frameNo=(frameNo+1)%24; drawFace();
}

void setup(){
  Serial.begin(KOALA_OLED_SERIAL_BAUD); delay(300);
  Wire.begin(KOALA_OLED_SDA,KOALA_OLED_SCL); oled.begin(); oled.setContrast(180);
  showFace("idle","mouth ready",2200);
  StaticJsonDocument<160> boot; boot["type"]="boot"; boot["device"]="heltec-oled"; boot["fw"]=KOALA_OLED_FW_VERSION; serializeJson(boot,Serial); Serial.println();
}

void loop(){pollSerial();tick();delay(10);} 
