#pragma once
#include "avatar_render.h"

// Orthographic adaptation of the exported 3D poses. Full character repaint
// includes the previous silhouette, so head turns and color changes leave no trails.
constexpr int FACE_X=0, FACE_Y=72, FACE_WIDTH=172, FACE_HEIGHT=176;
constexpr float AVATAR_SCALE=.44f;

struct AvatarProjection {
  float xx,xy,xz,yx,yy,yz;
  AvatarProjection(const AvatarExpression& e) {
    constexpr float radians=.01745329252f;
    float cx=cosf(e.headX*radians),sx=sinf(e.headX*radians);
    float cy=cosf(e.headY*radians),sy=sinf(e.headY*radians);
    float cz=cosf(e.headZ*radians),sz=sinf(e.headZ*radians);
    xx=cz*cy; xy=cz*sy*sx-sz*cx; xz=cz*sy*cx+sz*sx;
    yx=sz*cy; yy=sz*sy*sx+cz*cx; yz=sz*sy*cx-cz*sx;
  }
};

struct ProjectedEllipse {
  float cx,cy,a,b,c;
  ProjectedEllipse(const AvatarNode& n,const AvatarProjection& p) {
    cx=p.xx*n.x+p.xy*n.y+p.xz*n.z;
    cy=p.yx*n.x+p.yy*n.y+p.yz*n.z;
    float co=cosf(n.angle*.01745329252f),si=sinf(n.angle*.01745329252f);
    float ux=(p.xx*co+p.xy*si)*n.width*.5f;
    float uy=(p.yx*co+p.yy*si)*n.width*.5f;
    float vx=(-p.xx*si+p.xy*co)*n.height*.5f;
    float vy=(-p.yx*si+p.yy*co)*n.height*.5f;
    float wx=p.xz*n.depth*.5f,wy=p.yz*n.depth*.5f;
    float aa=ux*ux+vx*vx+wx*wx,bb=ux*uy+vx*vy+wx*wy,cc=uy*uy+vy*vy+wy*wy;
    float determinant=fmaxf(.001f,aa*cc-bb*bb);
    a=cc/determinant; b=-2*bb/determinant; c=aa/determinant;
  }
  bool contains(float x,float y) const {
    x-=cx; y-=cy; return a*x*x+b*x*y+c*y*y<=1;
  }
};

struct ProjectedEye {
  float cx,cy,ix,iy,jx,jy,hw,hh,r;
  ProjectedEye(const AvatarEye& e,float center,float openness,const AvatarProjection& p,float shake) {
    float x=center+e.x+shake,y=34+e.y;
    float z=sqrtf(fmaxf(0,120*120-x*x-y*y));
    cx=p.xx*x+p.xy*y+p.xz*z; cy=p.yx*x+p.yy*y+p.yz*z;
    float co=cosf(e.angle*.01745329252f),si=sinf(e.angle*.01745329252f);
    float ux=p.xx*co+p.xy*si,uy=p.yx*co+p.yy*si;
    float vx=-p.xx*si+p.xy*co,vy=-p.yx*si+p.yy*co;
    float det=ux*vy-uy*vx;
    if(fabsf(det)<.01f) det=.01f;
    ix=vy/det; iy=-vx/det; jx=-uy/det; jy=ux/det;
    hw=e.width*.5f; hh=fmaxf(5,e.height*openness)*.5f; r=fminf(hw,hh);
  }
  bool contains(float x,float y) const {
    x-=cx; y-=cy;
    float u=fmaxf(fabsf(ix*x+iy*y)-(hw-r),0);
    float v=fmaxf(fabsf(jx*x+jy*y)-(hh-r),0);
    return u*u+v*v<=r*r;
  }
};

static void renderFaceFrame(uint16_t* pixels,const AvatarExpression& e,
                            float openness,float requestedGaze,uint32_t now=0) {
  AvatarProjection p(e);
  ProjectedEllipse arms[]={ProjectedEllipse(AVATAR_NODES[0],p),ProjectedEllipse(AVATAR_NODES[1],p)};
  float t=(now%60000)*.001f;
  float dx=e.bodyMotion==AvatarMotion::Shake?3*sinf(t*35):
           e.bodyMotion==AvatarMotion::SlowDrift?4*sinf(t*1.4f):0;
  float dy=e.bodyMotion==AvatarMotion::SlowDrift?3*cosf(t*1.1f):0;
  float shake=e.eyeMotion==AvatarMotion::Shake?2*sinf(t*40):0;
  float gaze=avatarGazeOffset(e,requestedGaze);
  ProjectedEye left(e.left,-(e.spacing+e.left.width)*.5f+gaze,openness,p,shake);
  ProjectedEye right(e.right,(e.spacing+e.right.width)*.5f+gaze,openness,p,shake);
  for(int y=0;y<FACE_HEIGHT;++y) {
    float my=(FACE_Y+y-160)/AVATAR_SCALE-dy;
    for(int x=0;x<FACE_WIDTH;++x) {
      float mx=(x-86)/AVATAR_SCALE-dx;
      bool sphere=mx*mx+my*my<=120*120;
      bool body=sphere || arms[0].contains(mx,my) || arms[1].contains(mx,my);
      uint16_t color=!body?AVATAR_BACKGROUND:
        sphere && (left.contains(mx,my)||right.contains(mx,my))?e.eyeColor:e.bodyColor;
      pixels[y*FACE_WIDTH+x]=(color>>8)|(color<<8);
    }
  }
}
