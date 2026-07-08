// Persistence of Vision Raytracer
// This data file makes a good starting point for developing tests and
// new data files.  It is also used as the benchmark for the timing tests.

#include "colors.inc"           // Standard colors library
#include "textures.inc"         // LOTS of neat textures.  Lots of NEW textures.

camera {
   location  <0, 1.5,-2>
   direction <0, 0,   1>
   up        <0, 1,   0>
   right   <4/3, 0,   0>
   look_at   <0, 0,   0>
}

// Light source (backlit)
light_source {<0, 30, 10> color White}

// A "sky sphere" to reflect in the glass
sphere {<0, 0, 0>, 1000 texture{pigment{ color DimGray } } }

// Crystal dish
intersection {
   sphere {<0, 0, 0>, 1}
   sphere {<0, 0.25, 0>, 0.75 inverse}
   plane  {y, 0.75 }
   texture {Glass3 finish{reflection 0.25 }}
   bounded_by { sphere { <0, 0, 0>, 1.1 } }
}

plane { y, -1 
   pigment {
      DMFDarkOak
      scale <0.75, 0.75, 1>
      translate <10, -0.45, 10>
      rotate <5, 30, 0.25>
   }
   finish {
      ambient 0.05
      diffuse 0.5
      reflection 0.35
      specular 0.9
      roughness 0.005
   }
}
