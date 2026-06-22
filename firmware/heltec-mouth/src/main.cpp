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
static uint32_t untilMs=0,lastMs=0,startMs=0;

static bool eq(const char*a,const char*b){return a&&b&&!strcasecmp(a,b);} 
static uint8_t phase(){return (uint8_t)(((millis()-startMs)/80)%24);}  // same beat as DualEye eye renderer

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
  int beat=(frameNo<12?frameNo:24-frameNo);
  if(eq(stateName,"speaking")){
    int open=4+beat;
    int width=44+(beat/2);
    oled.drawRBox(cx-width/2,cy-open,width,open*2,6);
    oled.setDrawColor(0);
    oled.drawRBox(cx-width/2+6,cy-open/2,width-12,max(3,open),4);
    oled.setDrawColor(1);
    oled.drawHLine(cx-width/2+5,cy,width-10);
  }else if(eq(stateName,"wake")||eq(stateName,"listening")){
    int nudge=(frameNo%6)-3;
    oled.drawHLine(cx-28,cy+nudge,56);
    oled.drawPixel(cx-34,cy+nudge); oled.drawPixel(cx+34,cy+nudge);
  }else if(eq(stateName,"thinking")){
    for(int x=-36;x<=36;x+=12)oled.drawDisc(cx+x,cy+(((x/12+frameNo)%2)?3:-3),2);
  }else if(eq(stateName,"action")){
    int sweep=(frameNo%16)-8;
    oled.drawHLine(cx-38,cy,76);
    for(int x=-32;x<=32;x+=16)oled.drawVLine(cx+x+sweep/3,cy-8,16);
  }else if(eq(stateName,"success")){
    int lift=(beat>6)?2:0;
    oled.drawLine(cx-34,cy-lift,cx-15,cy+8-lift); oled.drawLine(cx-15,cy+8-lift,cx+15,cy+8-lift); oled.drawLine(cx+15,cy+8-lift,cx+34,cy-lift);
  }else if(eq(stateName,"error")||eq(stateName,"blocked")){
    int dip=(beat>6)?2:0;
    oled.drawLine(cx-34,cy+7+dip,cx-15,cy-2+dip); oled.drawLine(cx-15,cy-2+dip,cx+15,cy-2+dip); oled.drawLine(cx+15,cy-2+dip,cx+34,cy+7+dip);
  }else{
    oled.drawHLine(cx-26,cy,52);
  }
}

static void drawDefinedSnout(){
  int cx=64, cy=35;
  int beat=(frameNo<12?frameNo:24-frameNo);
  int bob=(eq(stateName,"speaking")||eq(stateName,"wake"))?(beat/5-1):0;

  // Outer muzzle pads and bridge: stronger koala snout definition.
  oled.drawRFrame(cx-55,cy-22+bob,110,40,13);
  oled.drawEllipse(cx-24,cy-2+bob,28,18,U8G2_DRAW_ALL);
  oled.drawEllipse(cx+24,cy-2+bob,28,18,U8G2_DRAW_ALL);
  oled.drawRFrame(cx-18,cy-25+bob,36,16,7);
  oled.drawBox(cx-9,cy-17+bob,18,7);
  oled.setDrawColor(0);
  oled.drawPixel(cx-4,cy-14+bob); oled.drawPixel(cx+4,cy-14+bob);
  oled.setDrawColor(1);
  oled.drawVLine(cx,cy-10+bob,9);
  oled.drawRFrame(cx-43,cy-9+bob,86,25,7);
  drawMouthShape(cx,cy+3+bob);

  // Small cheek ticks make the snout easier to read on the tiny OLED.
  oled.drawPixel(cx-46,cy+5+bob); oled.drawPixel(cx-50,cy+1+bob); oled.drawPixel(cx-46,cy-3+bob);
  oled.drawPixel(cx+46,cy+5+bob); oled.drawPixel(cx+50,cy+1+bob); oled.drawPixel(cx+46,cy-3+bob);
}

static void drawFace(){
  oled.clearBuffer();
  header();
  drawDefinedSnout();
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
  active=true; startMs=millis(); frameNo=0; lastMs=0; untilMs=millis()+(uint32_t)(duration>0?duration:KOALA_FACE_DEFAULT_DURATION_MS);
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
  uint32_t now=millis(); if(now-lastMs<80)return;
  lastMs=now; frameNo=phase(); drawFace();
}

void setup(){
  Serial.begin(KOALA_OLED_SERIAL_BAUD); delay(300);
  Wire.begin(KOALA_OLED_SDA,KOALA_OLED_SCL); oled.begin(); oled.setContrast(200);
  showFace("idle","mouth ready",2200);
  StaticJsonDocument<160> boot; boot["type"]="boot"; boot["device"]="heltec-oled"; boot["fw"]=KOALA_OLED_FW_VERSION; serializeJson(boot,Serial); Serial.println();
}

void loop(){pollSerial();tick();delay(10);} 
