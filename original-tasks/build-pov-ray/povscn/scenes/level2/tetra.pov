// Persistence Of Vision raytracer version 2.0 sample file.

// By ???

#include "shapes.inc"
#include "shapes2.inc"
#include "colors.inc"
#include "textures.inc"

camera {
   location <0.0, 30.0, -200.0>
   direction <0.0, -0.15, 1.0>
   up <0.0, 1.0, 0.0>
   right <4/3, 0.0, 0.0>
}

#declare Tetra = object {
   Tetrahedron

   pigment { Gold }
   finish {
      crand 0.01
      ambient 0.1
      diffuse 0.7
      reflection 0.4
      brilliance 6.0
   }
}

object { Tetra
   scale 10
   rotate -45*y
   translate <-10.0, 0.0, -105.0>
}

object { Tetra
   scale 10
   rotate -40*y
   translate <75.0, 0.0, 50.0>
}

object { Tetra
   scale 10
   rotate 30*y
   translate <-60.0, 0.0, -50.0>
}

object { Tetra
   scale 10.0
   rotate -75*y
   translate <60.0, 0.0, -65.0>
}

sphere { <-50.0, 50.0, 100.0>, 100.0
   pigment { White }
   finish {
      crand 0.01
      ambient 0.05
      diffuse 0.1
      reflection 0.97
      brilliance 4.0
   }
}

plane { y, -50.0
   pigment {
      checker colour Blue colour Gray
      quick_color Blue
      scale 40.0
   }
   finish {
      crand 0.01
      ambient 0.3
      diffuse 0.7
      reflection 0.1
      brilliance 3.0
   }
}

plane { y, 500.0
   pigment {
      Bright_Blue_Sky
      quick_colour red 0.5 green 0.5 blue 0.8
      scale <2000.0, 500.0, 1000.0>
   }
   finish {
      crand 0.05
      ambient 0.7
      diffuse 0.0
   }
}

light_source { <60.0, 60.0, -200.0> colour White }

light_source { <-60.0, 60.0, -200.0> colour White }
