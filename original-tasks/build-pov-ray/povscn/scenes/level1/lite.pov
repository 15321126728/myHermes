// Persistence Of Vision raytracer version 2.0 sample file.

// a very simple file to demonstrate image_map  - CdW
// 7/29/91
// NOTE: Requires "rough.gif"

#include "colors.inc"
#include "textures.inc"

#declare Texture0 = /* Planar image map */
texture {
   pigment {
       image_map { gif "rough.gif" map_type 0 interpolate 0 }
   }
}

camera {
   location  <0, 20, -125>
   direction <0,  0,    2>
   up        <0,  1,    0>
   right   <4/3,  0,    0>
   look_at   <0, 25,    0> 
}

// Sphere with radius 30 (diameter 60 )

sphere { <0, 25, 0>, 20
   texture {Glass}
}

plane { z, 150 
   texture { Texture0 scale 90 }
}

light_source {<100, 140, -130> colour White }
