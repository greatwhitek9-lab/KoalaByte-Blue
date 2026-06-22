#include <Arduino.h>
#include <string.h>
#include "config.h"
#include "killerkoala_ai_face.h"

#if ENABLE_DISPLAY_BOOT_ANIMATION
#include <TFT_eSPI.h>
static TFT_eSPI tft=TFT_eSPI();
static bool inited=false, active=false;
static char faceState[18]="idle", faceMsg[64]="";
static uint32_t untilMs=0,lastMs=0;
static uint8_t frameNo=0;

static uint16_t c(uint8_t r,uint8_t g,uint8_t b){return tft.color565(r,g,b);}
static bool eq(const char*a,const char*b){return a&&b&&!strcasecmp(a,b);}
static void ready(){if(!inited){tft.init();tft.setRotation(DISPLAY_ROTATION);inited=true;}}
static void koalaEar(int x,int y,int r,uint16_t glow){
  tft.drawCircle(x,y,r+3,glow); tft.fillCircle(x,y,r,c(18,30,43));
  tft.fillCircle(x,y,r/2,c(58,72,84)); tft.drawCircle(x,y,r,c(94,114,129));
}
static void eye(int x,int y,uint16_t fg,bool left){
  int pulse=(eq(faceState,"wake")||eq(faceState,"speaking"))?(frameNo<12?frameNo:24-frameNo):0;
  int rx=38+pulse/2, ry=eq(faceState,"action")?12:15;
  if(eq(faceState,"listening")&&(frameNo==6||frameNo==7)) ry=3;
  uint16_t dark=c(2,6,11), lid=c(4,10,18);
  int lean=left?-5:5, cut=eq(faceState,"action")?13:9;
  tft.drawRoundRect(x-rx-9,y-ry-10,rx*2+18,ry*2+20,14,fg);
  tft.fillTriangle(x-rx,y-ry,x+rx,y-ry+lean,x+rx-cut,y+ry,fg);
  tft.fillTriangle(x-rx,y-ry,x-rx+cut,y+ry,x+rx-cut,y+ry,fg);
  tft.fillCircle(x+(left?9:-9),y+1,6,dark);
  tft.fillCircle(x+(left?12:-12),y-2,2,TFT_WHITE);
  if(left)tft.fillTriangle(x-rx-6,y-ry-18,x+rx+4,y-ry-12,x+rx+4,y-ry-5,lid);
  else tft.fillTriangle(x+rx+6,y-ry-18,x-rx-4,y-ry-12,x-rx-4,y-ry-5,lid);
  if(eq(faceState,"thinking")) tft.drawFastVLine(x-rx+(frameNo*rx*2)/23,y-ry-7,ry*2+14,TFT_WHITE);
}
static void drawFace(){
  ready(); int w=tft.width(),h=tft.height(),cx=w/2,cy=h/2+3;
  uint16_t uv=c(165,75,255), green=c(50,255,113), accent=eq(faceState,"error")?c(255,82,40):green;
  tft.fillScreen(c(2,5,11)); tft.drawRect(0,0,w,h,accent); tft.drawRoundRect(8,8,w-16,h-16,18,c(24,82,96));
  for(int x=0;x<w;x+=20)tft.drawFastVLine(x,48,h-92,c(10,31,42));
  for(int y=48;y<h-38;y+=20)tft.drawFastHLine(0,y,w,c(10,31,42));
  tft.setTextDatum(TL_DATUM); tft.setTextSize(2); tft.setTextColor(c(35,227,255),c(2,5,11)); tft.drawString("KILLERKOALA",15,13);
  tft.setTextSize(1); tft.setTextColor(c(255,226,78),c(2,5,11)); tft.drawString("KOALA AI COMPANION",18,34);
  tft.fillRoundRect(max(8,w-155),9,145,32,9,c(5,15,23)); tft.drawRoundRect(max(8,w-155),9,145,32,9,accent);
  tft.setTextColor(accent,c(5,15,23)); tft.drawString(faceState,max(17,w-146),27);
  int headW=min(w-48,310), headH=min(h-85,190);
  koalaEar(cx-headW/2+22,cy-headH/2+18,38,uv); koalaEar(cx+headW/2-22,cy-headH/2+18,38,green);
  tft.fillRoundRect(cx-headW/2,cy-headH/2,headW,headH,48,c(5,10,18)); tft.drawRoundRect(cx-headW/2,cy-headH/2,headW,headH,48,c(76,106,126));
  eye(cx-76,cy-18,uv,true); eye(cx+76,cy-18,green,false);
  tft.fillRoundRect(cx-15,cy+23,30,18,8,c(2,5,10)); tft.drawRoundRect(cx-15,cy+23,30,18,8,c(73,122,139));
  tft.fillRoundRect(10,h-34,w-20,25,8,c(5,15,23)); tft.drawRoundRect(10,h-34,w-20,25,8,accent);
  tft.setTextColor(c(222,248,244),c(5,15,23)); tft.drawString(faceMsg[0]?faceMsg:"wake word / AI interaction",18,h-26);
}
void showKillerKoalaAiFace(const char *state,const char *message,const char*,const char*,int,int duration_ms){
  snprintf(faceState,sizeof(faceState),"%s",state&&state[0]?state:"listening"); snprintf(faceMsg,sizeof(faceMsg),"%s",message?message:"");
  active=true; frameNo=0; lastMs=0; untilMs=millis()+(uint32_t)(duration_ms>0?duration_ms:KILLERKOALA_FACE_DEFAULT_DURATION_MS); drawFace();
}
void hideKillerKoalaAiFace(){active=false;}
bool isKillerKoalaAiFaceActive(){if(!active)return false; if((int32_t)(millis()-untilMs)>0){active=false;return false;} return true;}
void tickKillerKoalaAiFace(){if(!isKillerKoalaAiFaceActive())return; uint32_t now=millis(); if(now-lastMs<120)return; lastMs=now; frameNo=(frameNo+1)%24; drawFace();}
#else
void showKillerKoalaAiFace(const char*,const char*,const char*,const char*,int,int){}
void hideKillerKoalaAiFace(){}
bool isKillerKoalaAiFaceActive(){return false;}
void tickKillerKoalaAiFace(){}
#endif
