#include <Arduino.h>
#include <string.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include "config.h"

static Adafruit_ST7789 tft(&SPI1, KOALA_TFT_CS, KOALA_TFT_DC, KOALA_TFT_RST);
static bool active=false, ready=false;
static char stateName[18]="idle";
static char lineText[64]="";
static uint8_t frameNo=0;
static uint32_t untilMs=0,lastMs=0,startMs=0,lastGnssMs=0;
static char gnssLine[128]="", lastGnss[128]="";
static uint8_t gnssPos=0;

static bool eq(const char*a,const char*b){return a&&b&&!strcasecmp(a,b);} 
static uint8_t phase(){return (uint8_t)(((millis()-startMs)/80)%24);}  // same beat as DualEye eyes
static int beat(){return frameNo<12?frameNo:24-frameNo;}

static void sendGnssLine(const char* nmea){
#if KOALA_GNSS_ENABLED
  if(!nmea||!nmea[0])return;
  StaticJsonDocument<256> doc;
  doc["type"]="gnss_nmea"; doc["device"]="heltec-t114"; doc["transport"]="usb-cdc"; doc["nmea"]=nmea;
  serializeJson(doc,Serial); Serial.println();
#endif
}

static void beginGnss(){
#if KOALA_GNSS_ENABLED
  Serial1.begin(KOALA_GNSS_BAUD);
#endif
}

static void pollGnss(){
#if KOALA_GNSS_ENABLED
  while(Serial1.available()){
    char ch=(char)Serial1.read();
    if(ch=='\n'){
      gnssLine[gnssPos]='\0';
      if(gnssPos>6 && gnssLine[0]=='$'){
        snprintf(lastGnss,sizeof(lastGnss),"%s",gnssLine);
        uint32_t now=millis();
        if(now-lastGnssMs>=KOALA_GNSS_REPORT_MS){lastGnssMs=now; sendGnssLine(lastGnss);}      
      }
      gnssPos=0;
    }else if(ch!='\r'){
      if(gnssPos<sizeof(gnssLine)-1)gnssLine[gnssPos++]=ch; else gnssPos=0;
    }
  }
#endif
}

static void sendGnssStatus(){
  StaticJsonDocument<256> doc;
  doc["type"]="gnss_status"; doc["device"]="heltec-t114"; doc["transport"]="usb-cdc";
#if KOALA_GNSS_ENABLED
  doc["enabled"]=true; doc["baud"]=KOALA_GNSS_BAUD; doc["last_nmea"]=lastGnss;
#else
  doc["enabled"]=false;
#endif
  serializeJson(doc,Serial); Serial.println();
}

static void powerPanel(bool on){
  pinMode(KOALA_TFT_VDD_CTL,OUTPUT); pinMode(KOALA_TFT_BL,OUTPUT); pinMode(KOALA_TFT_RST,OUTPUT);
  digitalWrite(KOALA_TFT_VDD_CTL,on?KOALA_TFT_POWER_ON_LEVEL:!KOALA_TFT_POWER_ON_LEVEL);
  digitalWrite(KOALA_TFT_BL,on?KOALA_TFT_BACKLIGHT_ON_LEVEL:!KOALA_TFT_BACKLIGHT_ON_LEVEL);
  digitalWrite(KOALA_TFT_RST,on?HIGH:LOW);
}

static void beginTft(){
  if(ready)return;
  powerPanel(true); delay(10);
  SPI1.begin();
  tft.init(KOALA_TFT_NATIVE_W,KOALA_TFT_NATIVE_H,SPI_MODE0);
  tft.setRotation(KOALA_TFT_ROTATION);
  tft.setSPISpeed(KOALA_TFT_SPI_HZ);
  tft.setTextWrap(false);
  tft.fillScreen(KOALA_COLOR_BG);
  ready=true;
}

static void text(int16_t x,int16_t y,const char*s,uint16_t fg,uint16_t bg=KOALA_COLOR_BG,uint8_t size=1){
  tft.setTextSize(size); tft.setTextColor(fg,bg); tft.setCursor(x,y); tft.print(s?s:"");
}

static void header(){
  tft.fillRoundRect(0,0,KOALA_TFT_W,18,4,KOALA_COLOR_GREEN);
  tft.setTextColor(KOALA_COLOR_BG,KOALA_COLOR_GREEN); tft.setTextSize(1); tft.setCursor(4,5); tft.print("KILLERKOALA");
  tft.setCursor(148,5); tft.print(stateName);
  tft.drawFastHLine(0,20,KOALA_TFT_W,KOALA_COLOR_CYAN);
}

static void fuzzyCheek(int cx,int cy,int side){
  uint16_t base=KOALA_COLOR_GREY, hi=KOALA_COLOR_FUZZ;
  for(int r=0;r<5;r++)tft.drawCircle(cx,cy,18+r*3,(r&1)?base:hi);
  for(int i=0;i<42;i++){
    int x=cx+((i*17+frameNo*3)%62)-31;
    int y=cy+((i*11+frameNo*5)%36)-18;
    tft.drawPixel(x,y,(i&1)?hi:base);
    if(i%5==0)tft.drawPixel(x+side,y,hi);
  }
}

static void drawSolidMouth(int cx,int cy,int bob){
  int b=beat();
  if(eq(stateName,"speaking")){
    int open=10+b*2, w=82+b*2;
    tft.fillRoundRect(cx-w/2,cy-open/2+bob,w,open,11,KOALA_COLOR_MOUTH);
    tft.drawRoundRect(cx-w/2,cy-open/2+bob,w,open,11,KOALA_COLOR_WARNING);
    tft.fillRoundRect(cx-w/2+14,cy-open/4+bob,w-28,max(5,open/2),7,KOALA_COLOR_MOUTH_DARK);
    tft.drawFastHLine(cx-w/2+12,cy+bob,w-24,KOALA_COLOR_WARNING);
  }else if(eq(stateName,"wake")||eq(stateName,"listening")){
    int n=(frameNo%6)-3; tft.fillRoundRect(cx-42,cy-4+n+bob,84,8,4,KOALA_COLOR_MOUTH);
  }else if(eq(stateName,"thinking")){
    for(int x=-42;x<=42;x+=14)tft.fillCircle(cx+x,cy+bob+(((x/14+frameNo)%2)?4:-4),4,KOALA_COLOR_MOUTH);
  }else if(eq(stateName,"action")){
    int s=(frameNo%16)-8; tft.fillRoundRect(cx-54,cy-6+bob,108,12,5,KOALA_COLOR_MOUTH);
    for(int x=-44;x<=44;x+=18)tft.drawFastVLine(cx+x+s/3,cy-11+bob,22,KOALA_COLOR_MOUTH_DARK);
  }else if(eq(stateName,"success")){
    tft.drawLine(cx-46,cy+bob,cx-20,cy+14+bob,KOALA_COLOR_GREEN); tft.drawLine(cx-20,cy+14+bob,cx+20,cy+14+bob,KOALA_COLOR_GREEN); tft.drawLine(cx+20,cy+14+bob,cx+46,cy+bob,KOALA_COLOR_GREEN);
    tft.drawLine(cx-46,cy+1+bob,cx-20,cy+15+bob,KOALA_COLOR_GREEN); tft.drawLine(cx+20,cy+15+bob,cx+46,cy+1+bob,KOALA_COLOR_GREEN);
  }else if(eq(stateName,"error")||eq(stateName,"blocked")){
    tft.drawLine(cx-46,cy+14+bob,cx-20,cy+bob,KOALA_COLOR_ERROR); tft.drawLine(cx-20,cy+bob,cx+20,cy+bob,KOALA_COLOR_ERROR); tft.drawLine(cx+20,cy+bob,cx+46,cy+14+bob,KOALA_COLOR_ERROR);
    tft.drawLine(cx-46,cy+16+bob,cx-20,cy+2+bob,KOALA_COLOR_ERROR); tft.drawLine(cx+20,cy+2+bob,cx+46,cy+16+bob,KOALA_COLOR_ERROR);
  }else{
    tft.fillRoundRect(cx-40,cy-3+bob,80,7,3,KOALA_COLOR_MOUTH);
  }
}

static void drawSnout(){
  int cx=120, cy=78, b=beat();
  int bob=(eq(stateName,"speaking")||eq(stateName,"wake"))?(b/5-1):0;
  fuzzyCheek(cx-52,cy+8+bob,-1); fuzzyCheek(cx+52,cy+8+bob,1);
  tft.drawRoundRect(cx-106,cy-42+bob,212,82,18,KOALA_COLOR_TEXT);
  tft.drawRoundRect(cx-92,cy-32+bob,84,64,22,KOALA_COLOR_FUZZ);
  tft.drawRoundRect(cx+8,cy-32+bob,84,64,22,KOALA_COLOR_FUZZ);
  tft.drawRoundRect(cx-36,cy-54+bob,72,34,12,KOALA_COLOR_CYAN);
  tft.fillRoundRect(cx-22,cy-40+bob,44,22,8,KOALA_COLOR_NOSE);
  tft.drawRoundRect(cx-22,cy-40+bob,44,22,8,KOALA_COLOR_GREY);
  tft.fillCircle(cx-10,cy-31+bob,3,KOALA_COLOR_GREY); tft.fillCircle(cx+10,cy-31+bob,3,KOALA_COLOR_GREY);
  tft.drawFastVLine(cx,cy-18+bob,21,KOALA_COLOR_TEXT);
  tft.drawRoundRect(cx-90,cy-6+bob,180,55,13,KOALA_COLOR_CYAN);
  drawSolidMouth(cx,cy+16,bob);
  for(int x=-104;x<=104;x+=52)tft.fillCircle(cx+x,cy+18+bob,3,KOALA_COLOR_FUZZ);
}

static void drawFace(){
  beginTft();
  tft.fillScreen(KOALA_COLOR_BG);
  header();
  drawSnout();
  tft.fillRoundRect(3,118,234,15,4,KOALA_COLOR_BG);
  tft.drawRoundRect(3,118,234,15,4,KOALA_COLOR_CYAN);
  char clipped[34]; snprintf(clipped,sizeof(clipped),"%s",lineText[0]?lineText:"color mouth ready");
  text(8,122,clipped,KOALA_COLOR_TEXT,KOALA_COLOR_BG,1);
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
  StaticJsonDocument<192> ack; ack["type"]="killerkoala_tft_ack"; ack["device"]="heltec-t114-color"; ack["state"]=state; ack["active"]=isActive(); ack["gnss_enabled"]=KOALA_GNSS_ENABLED; serializeJson(ack,Serial); Serial.println();
}

static void handleJson(const String&line){
  StaticJsonDocument<768> doc; if(deserializeJson(doc,line))return;
  const char*type=doc["type"]|"";
  if(!strcmp(type,"killerkoala_face")||!strcmp(type,"ai_face")){
    bool enabled=doc["enabled"]|true; const char*state=doc["state"]|"listening";
    if(!enabled){active=false;beginTft();tft.fillScreen(KOALA_COLOR_BG);sendAck("hidden");return;}
    showFace(state,doc["message"]|"",doc["duration_ms"]|KOALA_FACE_DEFAULT_DURATION_MS); sendAck(state);
  }else if(!strcmp(type,"gnss_status")){
    sendGnssStatus();
  }else if(!strcmp(type,"screen")){
    active=false; beginTft(); tft.fillScreen(KOALA_COLOR_BG); sendAck("suppressed_for_app");
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
  Serial.begin(KOALA_TFT_SERIAL_BAUD); delay(300);
  beginTft(); beginGnss(); showFace("idle","color mouth + GNSS ready",2200);
  StaticJsonDocument<192> boot; boot["type"]="boot"; boot["device"]="heltec-t114-color"; boot["fw"]=KOALA_TFT_FW_VERSION; boot["transport"]="usb-cdc"; boot["gnss_enabled"]=KOALA_GNSS_ENABLED; serializeJson(boot,Serial); Serial.println();
}

void loop(){pollSerial();pollGnss();tick();delay(10);} 
