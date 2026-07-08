// Persistence of Vision Raytracer
// Cluster of mirrored spheres 
// This file is essentially a copy of a similar file in MTV, Rayshade and Vivid
// This may look better at high resolutions 
// with max_trace_level set to 10 or 15

#include "colors.inc"

camera { // This is an unusual camera since it is a converted file
   location <2.31, 1.43, 1.65>
   up <0, 0, 1>          // The Z axis is up and
   right <-4/3, 0, 0> // The negative X axis is right
   direction <0, -1.60746, 0> // Field of view 45 degrees
   sky <0, 0, 1>
   look_at <0, 0, -0.1>
}

sphere { <0, 0, 0>, 10000
   pigment { SkyBlue }
   finish { ambient 1 diffuse .5}
}

light_source { <4, 3, 2 > color Gray30 }
light_source { <1, -4, 4> color Gray30 }
light_source { <-3, 1, 5> color Gray30 }

plane { z, -0.5
   pigment { color red 1.0 green 0.75 blue 0.33 }
   finish { diffuse 1 }
} // ambient .15 .1 .045 

/*
union {
   sphere { <0.7, 0, 0>, 0.2 texture { pigment { Red }   finish { diffuse 0.7} } }
   sphere { <0, 0.7, 0>, 0.2 texture { pigment { Green } finish { diffuse 0.7} } }
   sphere { <0, 0, 0.7>, 0.2 texture { pigment { Blue }  finish { diffuse 0.7} } }
}
*/

sphere { <0, 0, 0>, 0.5
   normal {
      bumps 0.4
      //turbulence .5
      // octaves 5
      scale 0.025
      //scale 0.05
   }
   finish {
      ambient 0.03
      diffuse 1
      reflection 0.4
      phong 1
      phong_size 3
   }
   pigment { color red 0.5 green 0.45 blue 0.35 }
}

union {
   sphere { <0.272166, 0.272166, 0.544331>, 0.166667  }
   sphere { <0.643951, 0.172546, 0>, 0.166667  }
   sphere { <0.172546, 0.643951, 0>, 0.166667 }
   sphere { <-0.371785, 0.0996195, 0.544331>, 0.166667  }
   sphere { <-0.471405, 0.471405, 0>, 0.166667  }
   sphere { <-0.643951, -0.172546, 0>, 0.166667  }
   sphere { <0.0996195, -0.371785, 0.544331>, 0.166667  }
   sphere { <-0.172546, -0.643951, 0>, 0.166667  }
   sphere { <0.471405, -0.471405, 0>, 0.166667  }

   pigment { color red 0.5 green 0.45 blue 0.35 }
   finish {
      ambient 0.035
      reflection 0.4
      diffuse 1
      phong 1 
      phong_size 3
   }
}

