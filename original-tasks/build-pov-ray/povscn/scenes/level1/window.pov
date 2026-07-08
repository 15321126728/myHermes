// Persistence Of Vision raytracer version 2.0 sample file.

// By Aaron a. Collins

/* Window Highlighting Scene by Aaron a. Collins */
/* This file is hereby released to the public domain. */

#include "colors.inc"

/* Someone to take in the breathtaking view... */

camera {
   location  <0, 20, -100>
   direction <0,  0,    1>
   up        <0,  1,    0>
   right   <4/3,  0,    0>
}

/* Put down the beloved famous raytrace green/yellow checkered floor */

plane { y, -10
   pigment {
      checker colour Yellow colour Green
      scale 20
   }
   finish {ambient 0.1 diffuse 0.9}
}

/*
 Now a CBlue Plastic sphere floating in space over the ground - note that no 
 Phong or specular reflection is given.  Any would conflict with the window
 "highlights" by showing that they are not exactly in the mirror direction!
*/

sphere { <0, 25, 0>, 40
   pigment {Blue}
   finish {reflection 0.8 ambient 0.3 diffuse 0.7}
}

/*
 a wall with a window frame to block the light source and cast the shadows
*/

union {
   triangle { <-1000, -1000, 0>, <1000, 4, 0>, <1000, -1000, 0>}
   triangle { <-1000, -1000, 0>, <1000, 4, 0>, <-1000, 4, 0>}
   triangle { <4, 4, 0>, <-1000, 21, 0>, <-1000, 4, 0>}
   triangle { <4, 4, 0>, <-1000, 21, 0>, <4, 21, 0>}
   triangle { <-1000, 21, 0>, <1000, 1000, 0>, <-1000, 1000, 0>}
   triangle { <-1000, 21, 0>, <1000, 1000, 0>, <1000, 21, 0>}
   triangle { <1000, 4, 0>, <17, 21, 0>, <1000, 21, 0>}
   triangle { <1000, 4, 0>, <17, 21, 0>, <17, 4, 0>}
   triangle { <4, 12, 0>, <17, 13, 0>, <4, 13, 0>}
   triangle { <4, 12, 0>, <17, 13, 0>, <17, 12, 0>}
   triangle { <10, 21, 0>, <11, 4, 0>, <11, 21, 0>}
   triangle { <10, 21, 0>, <11, 4, 0>, <10, 4, 0>}
   translate <39, 89, -120>

   pigment {Black}
   finish {ambient 1 diffuse 0}
}

/*
  Now, the 4 actual "panes" to be reflected back onto the sphere for psuedo-
  "highlights".  They are not exactly co-incident with where the actual light
  source is, because they would block the light.  They are very near by where
  the openings are in the black wall above, close enough to give the proper
  illusion.  This is massive cheating, but then, this isn't reality, you see.
*/

union {
   triangle { <4, 21, 0>, <10, 13, 0>, <10, 21, 0>}
   triangle { <4, 21, 0>, <10, 13, 0>, <4, 13, 0>}

   triangle { <11, 21, 0>, <17, 13, 0>, <11, 13, 0>}
   triangle { <11, 21, 0>, <17, 13, 0>, <17, 21, 0>}

   triangle { <4, 12, 0>, <10, 4, 0>, <4, 4, 0>}
   triangle { <4, 12, 0>, <10, 4, 0>, <10, 12, 0>}

   triangle { <11, 12, 0>, <17, 4, 0>, <11, 4, 0>}
   triangle { <11, 12, 0>, <17, 4, 0>, <17, 12, 0>}
   scale 15
   translate <20, 90, -100>

   pigment {White}
   finish {ambient 1 diffuse 0}
}


/* a Light above the sphere, behind the camera and window frame for shadows */

light_source {<50, 111, -130> colour White}
