// Persistence Of Vision raytracer version 2.0 sample file.

// Sample file:  A good starting point for your own test images.

#include "colors.inc"

camera {
   location  <0, 20,-100>
   direction <0,  0,   1>
   up        <0,  1,   0>
   right   <4/3,  0,   0>
}

plane { y, -10
   pigment {White}
   finish {ambient 0.2 diffuse 0.8}
}

sphere { <0, 25, 0>, 40
   pigment {Red}
   finish {
      ambient 0.15
      diffuse 0.75
      phong 1
      phong_size 100
   }
}

light_source {<100, 120, -40> colour White}
