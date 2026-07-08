// Persistence Of Vision raytracer version 2.0 sample file.

#include "colors.inc"
#include "textures.inc"

camera {
   location  <0, 20,-125>
   direction <0,  0,   2>
   up        <0,  1,   0>
   right   <4/3,  0,   0>
   look_at   <0, 25,   0> 
}

sphere { <0, 25, 0>, 20
   pigment {Clear}
   finish {
      ambient 0.0
      diffuse 0.0
      specular 0.5
      roughness 0.0001
      reflection 0.2
      refraction 1.0
      ior 1.5
   }
}

sphere { <0, 0, 0>, 200
   pigment {
      Bright_Blue_Sky
      scale <30, 10, 10>
   }
   finish {
      ambient 1
      diffuse 0.8
   }
}

light_source { <100, 140, -130> colour red 0.7 green 0.7 blue 0.7}
