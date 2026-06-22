#include <Arduino.h>
#include <string.h>
#include "config.h"
#include "killerkoala_ai_face.h"

#if ENABLE_DISPLAY_BOOT_ANIMATION
#include <TFT_eSPI.h>
static TFT_eSPI tft=TFT_eSPI();
static bool inited=false, active=false;
static char faceState[18]="idle", faceMsg[64]="";
static uint32_t untilMs=0,lastMs=0,startMs=0;
static uint8_t frameNo=0;

static uint16_t c(uint8_t r,uint8_t g,uint8_t b){return tft.color565(r,g,b);}
static bool eq(const char*a,const char*b){return a&&b&&!strcasecmp(a,b);}
static void ready(){if(!inited){tft.init();tft.setRotation(DISPLAY_ROTATION);inited=true;}}
static uint8_t phase(){return (uint8_t)(((millis()-startMs)/80)%24);}  // shared eye/mouth timing target

static void drawHud(uint16_t accent){
  int w=tft.width(),h=tft.height();
  tft.fillScreen(c(2,5,11));
  tft.drawRect(0,0,w,h,accent);
  for(int x=0;x<w;x+=20)tft.drawFastVLine(x,20,h-40,c(8,26,36));
  for(int y=20;y<h-20;y+=20)tft.drawFastHLine(0,y,w,c(8,26,36));
  tft.setTextDatum(TL_DATUM); tft.setTextSize(1);
  tft.setTextColor(c(35,227,255),c(2,5,11)); tft.drawString("KILLERKOALA EYES",8,8);
  tft.setTextColor(accent,c(2,5,11)); tft.drawString(faceState,max(8,w-78),8);
}

static void drawEye(int x,int y,uint16_t fg,bool left){
  bool speaking=eq(faceState,"speaking"), wake=eq(faceState,"wake"), thinking=eq(faceState,"thinking"), action=eq(faceState,"action");
  bool success=eq(faceState,"success"), error=eq(faceState,"error")||eq(faceState,"blocked");
  int mouthBeat=(frameNo<12?frameNo:24-frameNo);
  int pulse=(speaking||wake||success)?mouthBeat:0;
  int jitter=action?((frameNo%3)-1)*3:0;
  int rx=46+pulse/2, ry=18;
  if(speaking)ry=16+(mouthBeat/3);      // eye squint opens/closes with the Heltec mouth
  if(eq(faceState,"listening")&&(frameNo==6||frameNo==7)) ry=3;
  if(action)ry=13;
  uint16_t dark=c(2,6,11), glow=fg, lid=c(4,10,18);
  int lean=(left?-6:6)+jitter;
  int cut=action?15:10;
  tft.drawRoundRect(x-rx-10+jitter,y-ry-12,rx*2+20,ry*2+24,14,glow);
  tft.fillTriangle(x-rx+jitter,y-ry,x+rx+jitter,y-ry+lean,x+rx-cut+jitter,y+ry,fg);
  tft.fillTriangle(x-rx+jitter,y-ry,x-rx+cut+jitter,y+ry,x+rx-cut+jitter,y+ry,fg);
  if(error){
    tft.drawLine(x-rx,y-ry-6,x+rx,y+ry+6,c(255,82,40));
    tft.drawLine(x-rx,y+ry+6,x+rx,y-ry-6,c(255,82,40));
  }else{
    int px=x+(left?12:-12)+jitter;
    if(thinking)px=x-rx+((frameNo*rx*2)/23);
    if(speaking)px+=left?(mouthBeat/3):-(mouthBeat/3);
    tft.fillCircle(px,y+1,7,dark); tft.fillCircle(px+2,y-3,2,TFT_WHITE);
  }
  if(left)tft.fillTriangle(x-rx-8,y-ry-20,x+rx+6,y-ry-13,x+rx+6,y-ry-5,lid);
  else tft.fillTriangle(x+rx+8,y-ry-20,x-rx-6,y-ry-13,x-rx-6,y-ry-5,lid);
  if(thinking)tft.drawFastVLine(x-rx+((frameNo*rx*2)/23),y-ry-8,ry*2+16,TFT_WHITE);
  if(success)tft.drawCircle(x,y,rx+14,c(50,255,113));
}

static void drawEyes(){
  ready(); frameNo=phase(); int w=tft.width(),h=tft.height(),cy=h/2;
  uint16_t uv=c(165,75,255), green=c(50,255,113), accent=(eq(faceState,"error")||eq(faceState,"blocked"))?c(255,82,40):green;
  drawHud(accent);
  drawEye(w/2-78,cy,uv,true);
  drawEye(w/2+78,cy,green,false);
  tft.fillRoundRect(10,h-28,w-20,20,6,c(5,15,23));
  tft.drawRoundRect(10,h-28,w-20,20,6,accent);
  tft.setTextColor(c(222,248,244),c(5,15,23)); tft.setTextSize(1);
  tft.drawString(faceMsg[0]?faceMsg:"eyes only - case forms head",18,h-22);
}

void showKillerKoalaAiFace(const char *state,const char *message,const char*,const char*,int,int duration_ms){
  snprintf(faceState,sizeof(faceState),"%s",state&&state[0]?state:"listening"); snprintf(faceMsg,sizeof(faceMsg),"%s",message?message:"");
  active=true; startMs=millis(); frameNo=0; lastMs=0; untilMs=millis()+(uint32_t)(duration_ms>0?duration_ms:KILLERKOALA_FACE_DEFAULT_DURATION_MS); drawEyes();
}
void hideKillerKoalaAiFace(){active=false;}
bool isKillerKoalaAiFaceActive(){if(!active)return false; if((int32_t)(millis()-untilMs)>0){active=false;return false;} return true;}
void tickKillerKoalaAiFace(){if(!isKillerKoalaAiFaceActive())return; uint32_t now=millis(); if(now-lastMs<80)return; lastMs=now; drawEyes();}
#else
void showKillerKoalaAiFace(const char*,const char*,const char*,const char*,int,int){}
void hideKillerKoalaAiFace(){}
bool isKillerKoalaAiFaceActive(){return false;}
void tickKillerKoalaAiFace(){}
#endif
