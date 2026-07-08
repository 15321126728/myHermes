// Persistence Of Vision raytracer version 2.0 sample file.

// By Ville Saari
// Copyright (c) 1991 Ferry Island Pixelboys
/*
*
* POV-Ray scene description for 'Pac Man doing his favourite job'
* 
* Created: 03-Jan-91
* Updated: 05-Jan-91
*
* You will need pacman.iff which is included in this package.
*
* If you do some nice modifications or additions to this file, please send 
* me a copy. My Internet address is:
*
*         vsaari@niksula.hut.fi
*/

#include "shapes.inc"

camera {
   location <-80.0, 35.0, -140.0>
   direction <0.0, 0.0, 1.0>
   up  <0.0, 1.0, 0.0>
   right <1.244, 0.0, 0.0>
   sky <0.0, 1.0, 0.0>
   look_at <40.0, 10.0, 0.0>
}

/* The maze-textured ground */
plane { y, 0.0
   pigment {
      image_map { iff "pacman.iff" interpolate 2.0 }
      rotate 90*x
      scale 1600
      translate <-196.0, 0.0, 160.0>
   }
   finish {
      ambient 0.15
      diffuse 0.7
      reflection 0.5
   }
}

union { /* And now the world famous... Ta Da! ... pac man */
   /* Body */
   intersection {
      sphere { <0.0, 0.0, 0.0>, 30.0 }
      sphere { <0.0, 0.0, 0.0>, 28.0 inverse }

      union {
         plane { <0.0, +1.0, 0.0>, 0.0 rotate -35*x }
         plane { <0.0, -1.0, 0.0>, 0.0 rotate 10.0*x }
      }

      sphere { <0.0, 0.0, -29.0>, 1.5
         inverse
         rotate <16.0, -4.0, 0.0>
      }

      sphere { <0.0, 0.0, -29.0>, 1.5
         inverse
         rotate <16.0, 4.0, 0.0>
      }

      pigment { colour red 0.9 green 0.8 }
      finish {
         ambient 0.15
         diffuse 0.7
         specular 0.5
         roughness 0.1
      }
   }

   intersection {
      sphere { <0.0, 0.0, 0.0>, 28.0 }
      union {
         plane { +2*y, -2.0 rotate -35*x }
         plane { -2*y, -2.0 rotate 10*x }
      }

      pigment { colour red 0.5 }
      finish { ambient 0.25 diffuse 0.75 }
   }

   /* Tongue */
   union {
      sphere { <3.0, 0.0, -15.0>, 10.0 }
      sphere { <-3.0, 0.0, -15.0>, 10.0 }

      pigment { colour red 1.0 }
      normal {
         wrinkles 0.5
         scale 0.5
      }
      finish {
         ambient 0.15
         diffuse 0.7
         reflection 0.5
      }

      rotate -45*x
   }

   union { /* Right eye */
      sphere { <0.0, 0.0, 0.0>, 6.0
         pigment { colour red 1.0 green 1.0 blue 1.0 }
         finish {
            ambient 0.15
            diffuse 0.7
            reflection 0.5
         }
      }

      sphere { <0.0, 0.0, -2.3>, 4.0
         pigment { colour red 0.3 green 0.4 blue 0.8 }
         finish {
            ambient 0.15
            diffuse 0.7
            reflection 0.5
         }
      }
 
      sphere { <0.0, 0.0, -5.5>, 1.0
         pigment { colour red 0.0 green 0.0 blue 0.0 }
         finish {
            ambient 0.15
            diffuse 0.7
            reflection 0.5
         }
      }

      sphere { <0, 0, 0>, 1
         pigment { colour red 0.0 green 0.0 blue 0.0 }

         scale <9.0, 2.0, 9.0>
         translate <0.0, 8.0, 6.0>
         rotate -10.0*z
      }

      rotate <-25.0, -20.0, 0.0>
      translate -26.0*z
      rotate <25.0, 20.0, 0.0>
   }

   union { /* Left eye */
      sphere { <0.0, 0.0, 0.0>, 6.0
         pigment { colour red 1.0 green 1.0 blue 1.0 }
         finish {
            ambient 0.15
            diffuse 0.7
            reflection 0.5
         }
      }

      sphere { <0.0, 0.0, -2.3>, 4.0
         pigment { colour red 0.3 green 0.4 blue 0.8 }
         finish {
            ambient 0.15
            diffuse 0.7
            reflection 0.5
         }
      }

      sphere { <0.0, 0.0, -5.5>, 1.0
         pigment { colour red 0.0 green 0.0 blue 0.0 }
         finish {
            ambient 0.15
            diffuse 0.7
            reflection 0.5
         }
      }

      sphere { <0, 0, 0>, 1
         pigment { colour red 0.0 green 0.0 blue 0.0 }

         scale <9.0, 2.0, 9.0>
         translate <-0.0, 8.0, 6.0>
         rotate 10*z
      }

      rotate <-25.0, 20.0, 0.0>
      translate -26.0*z
      rotate <25.0, -20.0, 0.0>
   }

   bounded_by { sphere { <0.0, 0.0, -2.0>, 32.0 } }

   translate 32*y
}

/* Food... */
sphere { <0.0, 27.0, -25.0>, 4.0
   pigment { colour red 1.0 green 1.0 blue 1.0 }
   finish {
      ambient 0.15
      diffuse 0.7
      specular 2.0
      roughness 0.01
      reflection 0.6
   }
}

/* ... more food ... */
sphere { <0.0, 27.0, -45.0>, 4.0
   pigment { colour red 1.0 green 1.0 blue 1.0 }
   finish {
      ambient 0.15
      diffuse 0.7
      reflection 0.5
   }
}

/* ... and even more ... */
sphere { <0.0, 27.0, -65.0>, 4.0
   pigment { colour red 1.0 green 1.0 blue 1.0 }
   finish {
      ambient 0.15
      diffuse 0.7
      reflection 0.5
   }
}

/* ... uh ... yet more food ... */
sphere { <0.0, 27.0, -85.0>, 4.0
   pigment { colour red 1.0 green 1.0 blue 1.0 }
   finish {
      ambient 0.15
      diffuse 0.7
      reflection 0.5
   }
}

/* ... Yuck! ... no more please! */
sphere { <0.0, 27.0, -105.0>, 4.0
   pigment { colour red 1.0 green 1.0 blue 1.0 }
   finish {
      ambient 0.15
      diffuse 0.7
      reflection 0.5
   }
}

/* Click */
light_source { <60.0, 120.0, -170.0> colour red 1.0 green 1.0 blue 1.0 }
