// Persistence Of Vision raytracer version 2.0 sample file.

// By Tom Price

#include "shapes.inc"
#include "colors.inc"
#include "textures.inc"

camera {
   location <0.0, 30.0, -200.0>
   direction <0.0, -0.2, 1.0>
   up <0.0, 1.0, 0.0>
   right <4/3, 0.0, 0.0>
}

intersection {
   plane { z, 1.0 }
   plane { z, -1.0 inverse }
   plane { y, -60.0 }

   pigment {
      Apocalypse
      scale <50.0, 10.0, 20.0>
      rotate 30*y
   }
   finish {
      crand 0.01
      ambient 0.3
      diffuse 0.7
      reflection 0.3
      brilliance 3.0
   }

   scale <1.0, 1.0, 200.0>
}

intersection {
   sphere { <0, 0, 0>, 10000 }
   sphere { <0, 0, 0>, 9999 inverse }

   pigment {
      Bright_Blue_Sky
      scale <400.0, 50.0, 800.0>
      rotate -45*y
   }
   finish {
      crand 0.05
      ambient 0.3
      diffuse 0.5
   }

   translate <0.0, -9500.0, 0.0>
}

sphere { <0.0, 32.659862, 0.0>, 20.0
   pigment { White }
   finish {
      crand 0.01
      ambient 0.11
      diffuse 0.22
      reflection 0.7
      brilliance 5.0
   }
}

sphere { <0.0, 0.0, -23.09401>, 20.0
   pigment { Red }
   finish {
      crand 0.01
      ambient 0.11
      diffuse 0.22
      reflection 0.7
      brilliance 5.0
   }
   rotate -15*y
}

sphere { <0.0, 0.0, -23.09401>, 20.0
   pigment { Green }
   finish {
      crand 0.01
      ambient 0.11
      diffuse 0.22
      reflection 0.7
      brilliance 5.0
   }

   rotate -135*y
}

sphere { <0.0, 0.0, -23.09401>, 20.0
   pigment { Blue }
   finish {
      crand 0.01
      ambient 0.11
      diffuse 0.22
      reflection 0.7
      brilliance 5.0
   }

   rotate 105*y
}

sphere { <0.0, -32.659862, -23.09401>, 20.0
   pigment { Cyan }
   finish {
      crand 0.01
      ambient 0.11
      diffuse 0.22
      reflection 0.7
      brilliance 5.0
   }

   rotate -75*y
}

sphere { <0.0, -32.659862, -23.09401>, 20.0
   pigment { Magenta }
   finish {
      crand 0.01
      ambient 0.11
      diffuse 0.22
      reflection 0.7
      brilliance 5.0
   }

   rotate -195*y
}

sphere { <0.0, -32.659862, -23.09401>, 20.0
   pigment { Yellow }
   finish {
      crand 0.01
      ambient 0.11
      diffuse 0.22
      reflection 0.7
      brilliance 5.0
   }

   rotate 45*y
}

sphere { <0.0, -32.659862, -46.18802>, 20.0
   pigment { DimGray }
   finish {
      crand 0.01
      ambient 0.11
      diffuse 0.22
      reflection 0.7
      brilliance 5.0
   }

   rotate -15*y
}

sphere { <0.0, -32.659862, -46.18802>, 20.0
   pigment { Turquoise }
   finish {
      crand 0.01
      ambient 0.11
      diffuse 0.22
      reflection 0.7
      brilliance 5.0
   }

   rotate -135*y
}

sphere { <0.0, -32.659862, -46.18802>, 20.0
   pigment { Tan }
   finish {
      crand 0.01
      ambient 0.11
      diffuse 0.22
      reflection 0.7
      brilliance 5.0
   }

   rotate 105*y
}

light_source {
   <0, 0, 0> colour Orange

   looks_like {
      sphere { <0, 0, 0>, 75
         pigment { Orange }
         finish { ambient 1.0  diffuse 0.0 }
      }
   }

   translate 9800*y
   rotate <-5.0, 0.0, 2.0>
   translate -11000*y
}

light_source {
   <0, 0, 0> color White

   looks_like {
      sphere { <0, 0, 0>, 20
         pigment { White }
         finish { ambient 1.0 diffuse 0.0 }
      }
   }

   translate <60.0, 160.0, -200.0>
}

light_source {
   <0, 0, 0> color White

   looks_like {
      sphere { <0, 0, 0>, 20.0
         pigment { White }
         finish { ambient 1.0 diffuse 0.0 }
      }
   }

   translate <-60.0, 160.0, -200.0>
}
