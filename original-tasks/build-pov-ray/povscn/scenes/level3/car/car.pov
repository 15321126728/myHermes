// Persistence Of Vision raytracer version 2.0 sample file.

// By Jorge Arreguin

/*
 car.dat  POV-Ray Scene             February 27, '91

 By Jorge Arreguin
    i. Allende # 611
    Cortazar , Gto.
    Mexico  cp 38300
    
    Renders a Futuristic Car, making a diferent use of the imagemap
    NOTES: Requires "car_inc.gif" for imagemap. 540x350x16 color
    May require protected mode version of POV-Ray to run.  If you can't
    run POV-Ray, and you've already got all TSR's removed, then try
    scaling the imagemap down using PICLAB and changing the scaling in
    the texture block accordingly.  The results won't be as nice, but
    at least you'll be able to render it!

    To reduce by 1/2 from PICLAB:

            gload "car_inc.gif"   //The windshield glass
            unmap
            rescale 0.5
            map
            gsave "car_inc.gif"

    This image is designed using "right-hand" coordinates... z = height
    and y = depth.

*/

/*-----------------------------declaraciones------------------------*/

#include "shapes.inc"
#include "colors.inc"
#include "textures.inc"

#declare JA_Hyperboloid = quadric {
   <  1.0, -1.0, 1.0>,
   <  0.0,  0.0, 0.0>,
   <  0.0,  0.0, 0.0>,
   -0.6
}

#declare Near_Black = colour red 0.1 green 0.1 blue 0.1

#declare Llanta = intersection {
   sphere { <0, 0, 0>, 1 }
   object { JA_Hyperboloid scale < 0.7 0.3 0.7 > inverse }

   bounded_by { sphere { <0, 0, 0>, 1 } }
}

#declare Polvera =
   sphere {
      <0, 0, 0>, 1
      scale <0.8, 0.2, 0.8>

      texture {
         pigment { Gray }
         finish {
            reflection 0.3
            phong 0.8
            phong_size 10.0
         }
      }
   }

camera {
   location <0.0, -33.0, 0.0>
   direction <0.0, 2.0,  0.0>
   up  <0.0,  0.0,  1.0>
   right <4/3, 0.0, 0.0>
   rotate <-30.0, 0.0, 30.0>
}

light_source { <-10.0, -30.0, 50.0> colour White }

light_source { <40.0, -40.0, 45.0> colour White }

/*--------------------------------------- cuerpo --------------------*/

intersection {
   sphere {
      <0, 0, 0>, 1.0
      scale <10.0, 10.0, 4.0>
   }
   plane {
      x, 0.0
      rotate -16.2379*y
      translate -5.0*x
      inverse
   }
   plane { z, 0.01 }
   plane { z, 0.005 inverse }
   object {
      Cylinder_X
      scale <1.0, 5.0, 5.0>
   }

   bounded_by { sphere { <0.0, 0.0, 0.0>, 10.0 } }

   texture {
      pigment { Blue }
      finish { reflection 0.4 }
   }
}


union {
   intersection {
      sphere {
         <0, 0, 0>, 1
         scale <10.0, 10.0, 4.0>
      }
      plane {
         x, 0.0
         rotate -16.2379*y
         translate -5.0*x
         inverse
      }
      plane { z, 0.01 inverse }
      object {
         Cylinder_X
         scale <1.0, 5.0, 5.0>
      }
   }

   intersection {
      sphere {
         <0, 0, 0>, 1
         scale <3.352, 8.380, 3.352>
         rotate -16.2379*y
         translate -5.0*x
      }
      plane {
         x, 0.0
         rotate -16.2379*y
         translate -5.0*x
      }
      plane {
         x, 0.0
         rotate -64.0*y
         translate -5.0*x
         inverse
      }
      plane { z, 0.01 inverse }
      object {
         Cylinder_X
         scale <1.0, 5.0, 5.0>
      }
   }

   bounded_by { sphere { <0.0, 0.0, 0.0>, 10.0 } }

   texture {
      pigment {
         image_map { gif "car_inc.gif" interpolate 2.0 once }
         scale <18.6, 10.0, 1.0>
         translate <-8.38, -5.0, 0.0>
         quick_color Blue
      }
      finish {
         phong 0.8
         phong_size 20.0
         reflection 0.4
      }
   }
}

/*------------------------------- llantas ------------------------------*/

object {
   Llanta
   scale <1.907, 1.0, 1.907>
   translate <-4.0, -5.0, 0.907>

   texture {
      pigment { Near_Black }
      finish {
         phong 0.8
         phong_size 40.0
      }
   }
}

object {
   Llanta
   scale <1.907, 1.0, 1.907>
   translate <-4.0, 5.0, 0.907>

   texture {
      pigment { Near_Black }
      finish {
         phong 0.8
         phong_size 40.0
      }
   }
}

object {
   Llanta
   scale <1.435, 1.0, 1.435>
   translate <6.5, -5.0, 0.435>

   texture {
      pigment { Near_Black }
      finish {
         phong 0.8
         phong_size 40.0
      }
   }
}


object {
   Llanta
   scale <1.435, 1.0, 1.435>
   translate <6.5, 5.0, 0.435>

   texture {
      pigment { Near_Black }
      finish {
         phong 0.8
         phong_size 40.0
      }
   }
}

/*---------------------------- polveras -------------------------*/

object {
   Polvera
   scale <1.3, 1.0, 1.3>
   translate <6.5, 5.0, 0.435>
}

object {
   Polvera
   scale <1.3, 1.0, 1.3>
   translate <6.5, -5.0, 0.435>
}

object {
   Polvera
   scale <1.8, 1.0, 1.8>
   translate <-4.0, 5.0, 0.907>
}

object {
   Polvera
   scale <1.8, 1.0, 1.8 >
   translate <-4.0, -5.0, 0.907>
}

/*------------------------------ piso y bardas -----------------------------*/

plane {
   -z, 1.0

   texture {
      pigment {
         checker color Brown color Khaki
         rotate -90*x
         quick_color Maroon
      }
      finish { reflection 0.5 }
   }
}

plane { 
   -x, 11.0

   texture {
      pigment { Maroon }
      finish { reflection 0.5 }
   }
}

plane {
   y, 7.0

   texture {
      pigment { Maroon }
      finish { reflection 0.5 }
   }
}
