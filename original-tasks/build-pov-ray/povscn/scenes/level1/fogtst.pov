// Persistence Of Vision raytracer version 2.0 sample file.

#include "colors.inc"

camera {
   location  <0, 20, -100>
   direction <0,  0,    1>
   up        <0,  1,    0>
   right   <4/3,  0,    0>
}

fog {colour red 0.2 green 0.2 blue 0.2 distance 200}

/* Put down the beloved famous raytrace green/yellow checkered floor */
plane { y, -10
   pigment {
      checker colour Yellow colour Green
      scale 20
   }
   finish {
      ambient 0.2
      diffuse 0.8
   }
}

sphere { <0, 25, 0>, 40

   pigment {Red}
   finish {
      ambient 0.2
      diffuse 0.6
      phong 1.0
      phong_size 20
   }
}

sphere { <-100, 150, 200>,  20
   pigment {Magenta}
   finish {
      ambient 0.2
      diffuse 0.6
      phong 1.0
      phong_size 20
   }
}

sphere { <100, 25, 100>, 30
   pigment {Red}
   finish {
      ambient 0.2
      diffuse 0.6
      phong 1.0
      phong_size 20
   }
}

light_source {<100, 120, 40> colour White}
