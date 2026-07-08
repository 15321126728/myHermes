// Persistence Of Vision raytracer version 2.0, sample file.

// This data file makes a good starting point for developing tests and
// new data files.  It is also used as the benchmark for the timing tests.

#include "colors.inc"
#include "textures.inc"

camera {
   location  <0, 3,-10>
   direction <0, 0,  1>
   up        <0, 1,  0>
   right   <4/3, 0,  0>
   look_at   <0, 2, 0>
}

light_source {<10, 20, -30> color White}

// Sky sphere 
sphere { <0, 0, 0>, 10000
   pigment {color blue 1}
   finish {Luminous}
}

// Floor plane 
plane { y, 0
   pigment {NeonBlue}
   finish {ambient 0.15 diffuse 0.8}
}

// Sphere object 
sphere { <0, 3, 0>, 3
   pigment {Orange}
   finish {
      ambient 0.2
      diffuse 0.7
      phong 1
      phong_size 80
      brilliance 2
   }
}
