// Persistence Of Vision raytracer version 2.0 sample file.

// By David Buck

// This is the "classic" sunset scene by David k. Buck.  I'm resurrecting it
// because I always thought it looked very realistic...  - Aaron a. Collins

#include "colors.inc"

camera {
   location <0, 100, 200>
   direction <0, 0, -1>
   up <0, 1, 0>
   right <4/3, 0, 0>
}

/* Define the ocean surface */
plane { y, -10.0
   normal {
      waves 0.06
      frequency 5000.0
      scale 1000
   }
   finish { reflection 1.0 }
   pigment { color red 1.0 green 0.3 }
}

/* Put a floor underneath to catch any errant waves from the ripples */
plane { y, -11.0
   pigment { color red 1.0 green 0.3 }
   finish { ambient 1.0  diffuse 0.0  crand 0.05 }
}

/* Now draw the sky, a distant rear wall */
plane { z, -200.0
   pigment { colour red 1.0 green 0.3 }
   finish { ambient 0.3 diffuse 0.7 crand 0.05 }
}

/* Now to cast some light on the subject */
light_source {
   <0, 0, 0> colour red 1 green 1 blue 1

   looks_like {
      sphere {
         <0, 0, 0>, 20.0
         texture {
             pigment { colour red 1.0 green 0.6 filter 0.35 }
             finish { ambient 1.0 diffuse 0.0 }
         }
      }
   }

   translate <0.0, 30.0, -160.0>
}
