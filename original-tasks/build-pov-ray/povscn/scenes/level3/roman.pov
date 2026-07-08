// Persistence Of Vision raytracer version 2.0 sample file.
// By Rick Mallett of Carleton University,  Ottowa.
// First stage of the Tower of Pisa 
// Warning:  This picture can take a very long time to ray trace
// due to the large number of objects.  You have been warned :->  

#include "shapes.inc"
#include "colors.inc"
#include "textures.inc"

camera {
   location <0.0, 25.0, -150.0>
   direction <0.0, 0.1, 1.0>
   up <0.0, 1.0, 0.0>
   right <4/3, 0.0, 0.0>
}

#declare Beam = object {
   Cylinder_Y
   scale <0.5, 20.0, 0.5>
   translate 2.0*x
}

/* create a sample column for the base of the structure */

#declare BaseColumn = intersection {
   union {
      object { Beam }
      object { Beam rotate  -25.7*y }
      object { Beam rotate  -51.4*y }
      object { Beam rotate  -77.1*y }
      object { Beam rotate -102.8*y }
      object { Beam rotate -128.5*y }
      object { Beam rotate -154.2*y }
      object { Beam rotate -179.9*y }
      object { Beam rotate -205.6*y }
      object { Beam rotate -231.3*y }
      object { Beam rotate -257.0*y }
      object { Beam rotate -282.7*y }
      object { Beam rotate -308.4*y }
      object { Beam rotate -334.1*y }
   }

   plane { y, 40.0 }
   plane { -y, 0.0 }

   bounded_by {
      intersection {
         plane { y, 40.0 }
         plane { -y, 0.0 }
         object { Cylinder_Y scale <2.51 1.0 2.51> }
      }
   }

   texture {
      pigment {
         Red_Marble
         scale 10.0
         quick_color red 0.8 green 0.0 blue 0.0
      }
      finish {
         ambient 0.2
         diffuse 0.7
         reflection 0.1
      }
   }
}

/* and a rectangular pad to serve as a footing for the column */

#declare BasePad = object {
   UnitBox
   scale <4, 1, 4>

   texture {
      pigment {
         Red_Marble
         scale 10.0
         quick_color red 0.6 green 0.6 blue 0.4
      }
      finish {
         ambient 0.2
         diffuse 0.7
         reflection 0.1
      }
   }
}

/* and define a basic arch to span the columns */

#declare BaseArch = intersection {
   object { Cylinder_X scale <1.0, 12.5, 12.5> }
   object { Cylinder_X scale <1.0, 8.5, 8.5> inverse }
   plane { x, 2.0 }
   plane { -x, 2.0 }
   plane { -y, 0.0 }


   bounded_by {
      sphere { <0, 0, 0>, 1 scale <5.0, 13.0, 13.0> }
   }

   texture {
      pigment {
         Red_Marble
         scale 10.0
         quick_color red 0.8 green 0.8 blue 0.8
      }
      finish {
         ambient 0.2
         diffuse 0.7
         reflection 0.1
      }
   }
}

/* and finally define the first floor floor */

#declare BaseFloor = intersection {
   object { Cylinder_Y scale 50.0 }
   object { Cylinder_Y scale 40.0 inverse }
   plane { y, 2.0 }
   plane { -y, 2.0 }

   texture {
      pigment {
         Red_Marble
         scale 10.0
         quick_color red 0.8 green 0.8 blue 0.6
      }
      finish {
         ambient 0.2
         diffuse 0.7
         reflection 0.1
      }
   }
}

/* place a ring of 14 columns with footings around the base */

#declare FullColumn = union {
   object { BaseColumn translate <45.0, 0.0, 0.0> }
   object { BasePad    translate <45.0, -1.0, 0.0> }
   object { BasePad    translate <45.0, 41.0, 0.0> }
   object { BaseArch   translate <45.0, 42.0, 2.0> rotate <0.0, -12.85, 0.0> }
}

#declare Level1 = union {
   object { FullColumn }
   object { FullColumn rotate  -25.7*y }
   object { FullColumn rotate  -51.4*y }
   object { FullColumn rotate  -77.1*y }
   object { FullColumn rotate -102.8*y }
   object { FullColumn rotate -128.5*y }
   object { FullColumn rotate -154.2*y }
   object { FullColumn rotate -179.9*y }
   object { FullColumn rotate -205.6*y }
   object { FullColumn rotate -231.3*y }
   object { FullColumn rotate -257.0*y }
   object { FullColumn rotate -282.7*y }
   object { FullColumn rotate -308.4*y }
   object { FullColumn rotate -334.1*y }
   object { FullColumn rotate -334.1*y }
   object { BaseFloor translate 56.5*y }

   bounded_by {
      intersection { 
         object { Cylinder_Y scale <55.0, 1.0, 55.0> }
         plane { -y, 0.0 }
         plane { y, 60.0 }
      }
   }
}

object { Level1 }

/* Add the sky to the picture */
sphere {
   <0.0, 0.0, 0.0>, 300.0

   texture {
      pigment {
         bozo
         turbulence 0.5
         colour_map {
            [0.0 0.6   colour red 0.5 green 0.5 blue 1.0
                       colour red 0.5 green 0.5 blue 1.0]
            [0.6 0.8   colour red 0.5 green 0.5 blue 1.0
                       colour red 1.0 green 1.0 blue 1.0]
            [0.8 1.001 colour red 1.0 green 1.0 blue 1.0
                       colour red 0.8 green 0.8 blue 0.8]
         }
         scale <100.0, 20.0, 100.0>
         quick_color red 0.5 green 0.5 blue 1.0
      }
      finish {
         ambient 0.8
         diffuse 0.0
      }
   }
}

/* Define the desert floor */
plane {
   y, -2.0

   texture {
      pigment { colour red 1.0 green 0.66 blue 0.2 }
      normal {
         ripples 0.5
         frequency 2000.0
         scale 50000.0
      }
      finish {
         crand 0.05  /* This value dithers the colours */
         ambient 0.3
         diffuse 0.7
      }
   }
}

/* Add a light source */
light_source { <60.0, 50.0, -110.0> colour White }
