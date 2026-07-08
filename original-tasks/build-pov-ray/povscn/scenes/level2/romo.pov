// POV-Ray scene
// Fun reflections of a fertility symbol.
// A strange, but pleasant image.

#include "colors.inc"
#include "textures.inc"
#include "shapes.inc"

camera {
   location <0, 5, -16>
   direction <0, 0, 1.9>
   right <4/3, 0, 0>
   look_at <0, 4, 8>
}
#declare Radius = <0.4, 0.4, 0.4>
#declare Width = <0, 0, 2>

union {
   object { Cylinder_Y scale Radius translate Width }
   object { Cylinder_Y scale Radius translate Width rotate 30*y }
   object { Cylinder_Y scale Radius translate Width rotate 60*y }
   object { Cylinder_Y scale Radius translate Width rotate 90*y }
    
   object { Cylinder_Y scale Radius translate Width rotate -30*y }
   object { Cylinder_Y scale Radius translate Width rotate -60*y }
   object { Cylinder_Y scale Radius translate Width rotate -90*y }

   scale 4
   texture { Copper_Texture finish { reflection 0.5 } }
   translate <0, 4, 8>
}    

// Fertility symbol?
union {
   sphere { <0, 8, 8>, 2 }
   sphere { <2, 7, 8>, 1 }
   sphere { <-2, 7, 8>, 1 }
   sphere { <0, 4, 8>, 4 }
   sphere { <3, 2, 8>, 2 }
   sphere { <-3, 2, 8>, 2 }
   sphere { <4.5, 1, 8>, 1 }
   sphere { <-4.5, 1, 8>, 1 }

   scale <0.7, 0.7, 0.7>
   translate -3*z
   texture { pigment { Red } finish { phong 1 } }
}
  
// Floor
plane { y, 0
   texture { Brass_Valley scale 2 }
}

//object {
// sphere { <0, 0, 0>, 100 }
// texture { Blood_Sky }
//}

light_source { <3, 16, -8> color red 1 green 1 blue 1 }
