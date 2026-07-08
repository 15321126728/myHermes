// Persistence Of Vision raytracer version 2.0, sample file.

// a very simple file to demonstrate material_map  - CdW 
// 7/29/91 
// NOTE: Uses POVMAP.GIF

#include "colors.inc"
#include "textures.inc"

camera {
   location  <0,  0,-120>
   direction <0,  0,   2>
   up        <0,  1,   0>
   right   <4/3,  0,   0>
}

sphere { <0, 0, 0>, 25
   texture {
      material_map {
         gif "povmap.gif"
         /* Now a list of textures to map with instead of colors */

         texture {
            pigment {color red 0.3 green 0.1 blue 1}
            normal  {ripples 0.85 frequency 10 }
            finish  {specular 0.75}
            scale 5
         }

         texture {
            pigment {White} 
            finish {ambient 0 diffuse 0 reflection 0.9 specular 0.75}
         }

         texture {pigment{NeonPink} finish{Luminous}}

         texture {
            pigment {
               gradient y
               colour_map {
                  [0.00, 0.33  colour red 1 green 0 blue 0
                               colour red 0 green 0 blue 1]
                  [0.33, 0.66  colour red 0 green 0 blue 1
                               colour red 0 green 1 blue 0]
                  [0.66, 1.001 colour red 0 green 1 blue 0
                               colour red 1 green 0 blue 0]
               }
            }
            finish{specular 0.75}
            scale 8
         } 
      }
      scale 30
      translate <-15, -15, 0>
   }
}

/*Sky*/
sphere { <0, 0, 0>, 2000
   pigment {
      bozo
      turbulence 0.67
      colour_map {
         [0,   0.5   colour red 0.25 green 0.25 blue 0.5
                     colour red 0.25 green 0.25 blue 0.5]
         [0.5, 0.6   colour red 0.25 green 0.25 blue 0.5
                     colour red 0.7 green 0.7 blue 0.7]
         [0.6, 1.001 colour red 0.7 green 0.7 blue 0.7
                     colour red 0.3 green 0.3 blue 0.3]
      }
      scale <500, 200, 500.0>
   }
}

plane { y,-25
   pigment {
      checker  color Gold color Firebrick
      scale 10
   }
   finish {
      ambient 0.1
      diffuse 0.8
      /*reflection 0.6*/
   }
}

light_source {<100, 140, -130> colour White}
