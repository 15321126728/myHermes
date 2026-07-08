// Persistence Of Vision raytracer version 2.0 sample file.

// By Various and Sundry
//
// Revision Note:
// Reworked both the declared wood texture (turb and colormap) and
// the application of it on the floor plane.
// Note that wood doesn't really look like much until you get around
// 640x480.  Anti-aliasing helps even more to bring out the detail.  -dmf

#include "shapes.inc"
#include "colors.inc"
#include "textures.inc"

// a light tan wood with brown rings
#declare New_Tan_Wood = pigment {
   wood
   turbulence 0.03
   colour_map {
      [0.0 0.4  colour red 0.6 green 0.45 blue 0.25
                colour red 0.65 green 0.45 blue 0.25]
      [0.4 1.01 colour red 0.6 green 0.4 blue 0.2
                colour red 0.25 green 0.15 blue 0.05]
   }
}

camera {
   direction <0.0, 0.0, 1.0>
   up  <0.0, 1.0, 0.0>
   right <4/3, 0.0, 0.0>
   translate <0.0, 0.0, -56.0>
}


// A bowl
intersection {
   sphere { <0.0, 0.0, 0.0>, 1.0 }
   sphere { <0.0, 0.0, 0.0> 0.9 }
   plane { y, 0.5 }

   bounded_by {
      sphere { <0.0, 0.0, 0.0> 21.0 }
   }

   scale 20.0

   pigment { Red }
   finish {
      ambient 0.2
      diffuse 0.8
      reflection 0.1
   }
}

// Water
intersection {
   sphere { <0.0, 0.0, 0.0>, 1.0 }
   plane { y, 0.49 }

   bounded_by {
      sphere { <0.0, 0.0, 0.0>, 21.0 }
   }

   scale 19.5

   pigment { Black }
   normal {
      ripples 0.5
      frequency 100.0
      scale 100.0
   }
   finish {
      reflection 0.6
      refraction 0.6
      ior 1.2
   }
}


// Wood floor
plane { y, -20.0
   pigment {                  // seems to reduce "moire" effect on the grain
      New_Tan_Wood            // Think of a log, facing you...
      scale <2, 2, 1>         // z is infinite, so 1 is ok...
      rotate <0, 90, 0>       // turn the "log" to the x axis
      rotate <0.0, 0.0, 10.0> // tilt the log just a little bit
      translate <0, -4, 0>    // lift it to where the rings are larger
      rotate <5, 0, 0>        // tip it again, this time on x axis
   }

   finish {
      crand 0.015
      ambient 0.15
      diffuse 0.75
      reflection 0.1
   }
}


// Back wall
 plane { z, 100.0

    pigment {
       Red_Marble
       scale 100.0
    }
    finish {
      ambient 0.15
      diffuse 0.8
      reflection 0.1
   }
}

// A sky to reflect in the water
plane { y, 150.0

   pigment { colour red 0.5 green 0.5 blue 1.0 }
   finish {
      ambient 0.15
      diffuse 0.8
   }
}

// Light source
light_source { <100.0, 120.0, -130.0> colour White }
