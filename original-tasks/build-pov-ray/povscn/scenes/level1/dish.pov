// Persistence Of Vision raytracer version 2.0, sample file.

// By Aaron a. Collins

/* Scene Description of a Satellite Dish by Aaron A. Collins */
/* Made to test the quadric "Paraboloid" and "Cone" Shapes   */ 

#include "shapes.inc"
#include "colors.inc"

camera {
   location  <0, 0, -70>
   direction <0, 0,   1>
   up        <0, 1,   0>
   right   <4/3, 0,   0>
}

/* The basic dish */
union {
   intersection {
      object { Paraboloid_Y scale <30, 20, 30> }
      object { Paraboloid_Y scale <29, 19, 29> inverse }
      plane  { y, 20 }

      pigment { color red 0.8 green 0.2 blue 0.2 }
      finish {
         ambient 0.2
         diffuse 0.8
         phong 1.0
         phong_size 10
      }
   }

   /* The lna thingy at the focal point */
   union {
      object { QCone_Y
         scale <1, 10, 1> translate y*31
         clipped_by { plane { y, 31} plane {-y,  0} }
      }
      sphere { <0, 30, 0>, 2}

      pigment {color red 0 green 0.2 blue 0.8}
      finish {
         ambient 0.2
         diffuse 0.8
         phong 1.0
         phong_size 30
      }
   }

   /* The equatorial mount */
   object { Paraboloid_Y
      rotate x*180
      scale <30, 60, 30>
      texture {
         pigment { color red 0 green 0.8 blue 0.2 }
         finish {
            ambient 0.2
            diffuse 0.8
            phong 1.0
            phong_size 30
         }
      }
   }

   rotate <-30, -30, 0>
}

light_source {<100, 120, -130> colour White}

light_source {<-100, 100, -130> colour White}
