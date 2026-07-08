// Persistence of Vision Raytracer
// This data file makes a good starting point for developing tests and
// new data files.  It is also used as the benchmark for the timing tests.

#include "colors.inc"           // Standard colors library
#include "shapes.inc"           // Commonly used object shapes
//#include "shapes2.inc"          // More useful shapes
//#include "shapesq.inc"          // Quartic and other algebraic shapes. Neat!
#include "textures.inc"         // LOTS of neat textures.  Lots of NEW textures.
//#include "texture2.inc"         // SPECIAL!  Mike Miller's IONICS5 texture lib.

camera {
   location  <0, 3.5, -3.5>
   direction <0, 0,    1>
   up        <0, 1,    0>
   right   <4/3, 0,    0>
   look_at   <0, 0,    0>
}

// Light source

light_source {<-30, 11, +20>  color White  } 
light_source {< 31, 12, -20>  color White  }
light_source {< 32, 11, -20>  color LightGray }

#declare Pink_Gran_Texture =
texture {
   pigment{Pink_Granite turbulence 0}
   finish {
      Glossy
      ambient 0.15
      reflection 0.2
   }
}

union {
   sphere {<0, 0, 0>, 1.75}
   difference {
      object {UnitBox scale 1.5}
      // Clip some sqr holes in the box to make a 3D box frame
      object {UnitBox scale <1.51, 1.25, 1.25> }   // "clip" x
      object {UnitBox scale <1.25, 1.51, 1.25> }   // "clip" y
      object {UnitBox scale <1.25, 1.25, 1.51> }   // "clip" z
   }
   texture { Pink_Gran_Texture scale 0.25 }
   bounded_by { object {UnitBox scale 1.75 } }
   rotate y*45
}

//plane {y, -1.5  texture { Pink_Gran_Texture scale 0.05 } }
