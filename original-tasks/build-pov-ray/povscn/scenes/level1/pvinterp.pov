// Persistence Of Vision raytracer version 2.0 sample file.

// Imagemap interpolation test by CdW!
// NOTE: Requires "test.gif"

#include "colors.inc"

#declare Bilinear = 2.0
#declare Norm_Dist = 4.0

camera {
   location <0.0, 0.0, -25.0>
   direction <0.0, 0.0, 1.0>
   up  <0.0, 1.0, 0.0>
   right <4/3, 0.0, 0.0>
   look_at <0, 0, 0>
}

// Left hemisphere: Bilinear
sphere { <0.0, 0.0, 0.0>, 1.0
   clipped_by { plane { x, 0 } }

   pigment {
      image_map { gif "test.gif" interpolate Bilinear }
      quick_color Red
      translate <-0.5, -0.5, 0>
   }
   finish {
      ambient 0.2
      diffuse 0.7
   }

   scale 10
   translate -1*x
}

// Right hemisphere: norm_dist
sphere { <0.0, 0.0, 0.0>, 1.0
   clipped_by { plane { -x, 0 } }

   pigment {
      image_map { gif "test.gif" interpolate Norm_Dist }
      quick_color Blue
      translate <-0.5, -0.5, 0>
   }
   finish {
      ambient 0.2
      diffuse 0.7
   }

   scale 10
   translate 1*x
}

light_source { <100.0, 120.0, -130.0> colour White }

