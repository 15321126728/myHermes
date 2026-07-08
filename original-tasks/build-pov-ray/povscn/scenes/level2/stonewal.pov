// Persistence Of Vision raytracer version 2.0 sample file.

// By Dan Farmer
//    Minneapolis, mn
/*
      a pastoral scene with a granite stone fence.  This was never really
      "finished", but it works as it is.  Plenty of material to play around
      with here.  The basic building blocks are here... just use your
      imagination.
*/ 
#include "shapes.inc"
#include "colors.inc"
#include "textures.inc"

camera {
   location <50.0, 40.0, -350.0>
   look_at <-100.0, 0.0, 0.0>
   direction <0.0, 0.0, 2.0>
   right <4/3, 0.0, 0.0 >
}

/* Add light source */
light_source { <100.0, 200.0, -630.0> color White }

light_source { <50.0, 20000.0, 50.0> color White }

/* Add the sky to the picture */
sphere { <0.0, 0.0, 0.0>, 1000000.0
   pigment { SkyBlue }
   finish { diffuse 0 ambient 1 }
}

/* Grassy meadow */
plane { y, -2.0
   pigment { color red 0.2 green 1.0 blue 0.4 }
   finish {
      crand 0.05  /* This value dithers the colors */
      ambient 0.1
      diffuse 0.3
   }
   normal {
      waves 1.0
      frequency 2000.0
      scale 50000.0
   }
}

#declare Wall_Segment = object {
   Cube
   scale <8.0, 50.0, 100.0>

   pigment {
      granite
      quick_color White
   }
   finish {
      crand 0.05
      ambient 0.2
      diffuse 0.8
      brilliance 7.0
      reflection 0.1
      phong 1.0
      phong_size 60
   }
}

#declare Granite_Ball =
sphere { <0.0, 0.0, 10.0>, 10.0
   pigment {
      granite
      quick_color White
   }
   finish {
      crand 0.05
      ambient 0.2
      diffuse 0.8
      brilliance 7.0
      reflection 0.1
      phong 1.0
      phong_size 60
   }
}

#declare Column = object {
   Cube
   scale <12.0, 60.0, 12.0>

   pigment {
      granite
      quick_color White
   }
   finish {
      crand 0.05
      ambient 0.2
      diffuse 0.8
      brilliance 7.0
      reflection 0.1
      phong 1.0
      phong_size 60
   }
}

/* note: Granite column is 12 wide x 12 deep x 60 high
        Granite ball has a radius of 20 */
#declare Pillar = union {
   object { Column       translate  0*y }
   object { Granite_Ball translate 70*y }
}

/* Note: Wall segments are 100 units long, Pillars are 12 units "long" */
object { Pillar
   translate -106*z
}

object { Wall_Segment
   translate <-2.0, 0.0, -6.0 >
}

object { Pillar
   translate <0.0, 0.0, 0.0>
}

object { Wall_Segment
   translate <-2.0, 0.0, 112.0>
}

object { Pillar
   translate 112*z
}

object { Wall_Segment
   rotate -90*y
   translate <76.0, 0.0, 114.0>
}

object { Pillar
   translate <176.0, 0.0, 112.0>
}
