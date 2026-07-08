// Persistence Of Vision raytracer version 2.0 sample file.

// By David Buck

#include "colors.inc"

camera {
   location  <0, 10, 200>
   direction <0,  0,  -1>
   up        <0,  1,   0>
   right   <4/3,  0,   0>
   look_at   <0,130,-300>
}

/* Define the ocean surface */
plane { y, -10
   pigment {colour red 1 green 0.3}
   normal {
      waves 0.05
      frequency 5000
      scale 3000
   }
   finish {reflection 1}
}

/* Put a floor underneath to catch any errant waves from the ripples */
plane { y, -11
   pigment {colour red 1 green 0.3}
   finish {crand 0.05 ambient 1 diffuse 0}
}

/* Now draw the sky */
sphere { <0, 0, 0>, 300
   pigment {
      gradient <0, 1, 0>
      colour_map {
         [0, 0.8  colour red 1   green 0.3 blue 0
                  colour red 0.7 green 0.7 blue 1]
         [0.8, 1  colour red 0.7 green 0.7 blue 1
                  colour red 0.7 green 0.7 blue 1]
      }
      scale <300,  300,  300.0>
      quick_colour red 0.7  green 0.7 blue 1.0
   }
   finish {
      ambient 0.7 
      diffuse 0   /* we don't want clouds casting shadows on the sky */
   }
}

/* Put in a few clouds */
sphere { <0, 0, 0>, 259
   pigment {
      bozo
      turbulence 0.5
      colour_map {
         [0,   0.6   colour Clear
                     colour Clear]
         [0.6, 0.8   colour Clear
                     colour White]
         [0.8, 1.001 colour White
                     colour red 0.8 green 0.8 blue 0.8]
      }
      quick_colour red 0.7 green 0.7 blue 1
      scale <100, 20, 100>
   }
   finish {ambient 0.7 diffuse 0}
}

/* Now to cast some light on the subject */
light_source {<0, 0, -300> colour White rotate <10, 0, 0>}
