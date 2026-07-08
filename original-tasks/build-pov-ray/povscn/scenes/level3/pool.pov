// Persistence Of Vision raytracer version 2.0 sample file.

// By Dan Farmer
/* Script for a lawn with a swimming pool.
  Written by Dan Farmer.  Takes quite a while to render because of
  the many textures and waveforms used.  An interesting variation of this
  theme would be to change the view to look into the garden globe and see
  the rest of the scene as the reflection in the globe.

  As stated below, most of the garden globe structure was taken from the
  file "roman.pov".
*/

#include "colors.inc"
#include "shapes.inc"
#include "textures.inc"

/*
#declare Cube = intersection {
   plane { <0.0 0.0 1.0> 1.0 }
   plane { <0.0 0.0 -1.0> 1.0 }
   plane { <0.0 1.0 0.0> 1.0 }
   plane { <0.0 -1.0 0.0> 1.0 }
   plane { <1.0 0.0 0.0> 1.0 }
   plane { <-1.0 0.0 0.0> 1.0 }
   scale <1.0 1.0 1.0>
}
*/

/* Most of the garden globe is borrowed from "roman.dat"*/
/********************************************************/
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
      object { Beam rotate  -102.8*y }
      object { Beam rotate  -128.5*y }
      object { Beam rotate  -154.2*y }
      object { Beam rotate  -179.9*y }
      object { Beam rotate  -205.6*y }
      object { Beam rotate  -231.3*y }
      object { Beam rotate  -257.0*y }
      object { Beam rotate  -282.7*y }
      object { Beam rotate  -308.4*y }
      object { Beam rotate  -334.1*y }
   }
   plane { y, 20.0 }
   plane { -y, 0.0 }

   bounded_by {
      intersection {
         plane { y, 20.0 }
         plane { -y, 0.0 }
         object {
            Cylinder_Y
            scale <2.51, 1.0, 2.51>
         }
      }
   }

   texture {
      pigment {
         White_Marble
         scale 10.0
         quick_color White
      }
      finish {
         ambient 0.4
         diffuse 0.9
         reflection 0.1
      }
   }
}

/* and a rectangular pad to serve as a footing for the column */
#declare BasePad = object {
   Cube
   scale <4.0, 1.0, 4.0>

   bounded_by {
      sphere {
         <0, 0, 0>, 1
         scale <10.0, 3.0, 10.0>
      }
   }

   texture {
      pigment {
         White_Marble
         scale 10.0
         quick_color red 0.6 green 0.6 blue 0.4
      }
      finish {
         ambient 0.4
         diffuse 0.9
         reflection 0.1
      }
   }
}

#declare Globe = sphere {
   <0.0, 0.0, 0.0>, 5.0
   texture {
      finish { Mirror }
      pigment { Blue }
   }
}

#declare Garden_Globe = union {
   object { BaseColumn translate <0.0, 0.0, 0.0> }
   object { BasePad    translate <0.0, -1.0, 0.0> }
   object { BasePad    translate <0.0, 21.0, 0.0> }
   object { Globe      translate<0.0, 26.0, 0.0> }
}
/********************* End of Garden Globe Epic *******************************/

/* Everybody's gotta have a point of view. */
camera {
   location <0.0, 30.0, -120.0>
   direction <0.0, 0.0, 1.0>
   up  <0.0, 1.0, 0.0>
   right <4/3, 0.0, 0.0>
   look_at <0.0, 0.0, 0.0>
}

/* No, fool... i said _bud_ light! */
light_source { <100.0, 200.0, -200.0> colour White }

/* "The sky was the color of her eyes" */
/*             ... and just as cloudy! */
sphere {
   <0.0, -10000.0, -200.0>, 15000.0

   texture {
      pigment {
         Bright_Blue_Sky
         scale <7500.0, 1000.0, 5000.0>
         quick_color red 0.5 green 0.5 blue 1.0
      }
      finish {
         crand 0.05
         ambient 0.7
         diffuse 0.0
      }
   }
}

/* Plant a little grass, well mowed. */
plane {
   y, 0.0

   texture {
      pigment { Green }
      finish { crand 0.05 }
      normal {
         ripples 0.5
         frequency 2000.0
         scale 50000.0
      }
   }
}

/* Now, we pour the concrete and set the tiles...*/
difference {
   object {
      Cube
      scale <45.0, 10.0, 60.0>
   }
   object {
      Cube /* Inside box */
      scale <35.0, 11.0, 50.0>
   }

   translate <0.0, -8.0, 0.0>

   texture {
      pigment {
         checker colour DarkTurquoise colour White
         scale 2.0
         quick_color DarkTurquoise
      }
   }
}

/* Better put some water in the pool! */
object {
   Cube
   scale <35.0, 10.0, 50.0>
   translate <0.0, -9.0, 0.0>

   texture {
      pigment { LightBlue }
      normal {
         ripples 0.5
         frequency 100.0
         scale <5.0, 5.0, 10.0>
         translate <20.0, 4.0, -15.0>    /* Where the ball floats?? */
      }
      finish {
         crand 0.05
         reflection 0.5
         brilliance 3.0
         /*  refraction 1.0		{ Doesn't really help the scene any... }
         ior 1.2 ?? */
      }
   }
}

/* Let's add a diving board */
union {
   object {
      Cube                        /* The board itself */
      scale <6.0, 1.0, 30.0 >
      translate <0.0, 2.0, -30.0>
   }
   object {
      Cube                        /* a block under the board */
      scale <6.0, 2.0, 2.0 >
      translate <0.0, 1.0, -30.0>
   }

   texture {
      pigment {
         Cherry_Wood
         scale 0.02
         quick_color Brown
      }
      finish { crand 0.05 }
   }
}

/* Float a red and white striped ball in the pool */
sphere {
   <0.0, 0.0, 0.0>, 5.0

   translate <20.0, 4.0, -15.0>    /* Sorta right front center of pool */

   texture {
      pigment {
         gradient < 1.0, 1.0, 0.0 >
         colour_map {
            [0.00 0.25  colour White colour White ]
            [0.25 0.75  colour red 1.0  colour red 1.0]
            [0.75 1.001 colour White colour White ]
         }
         scale <7.0 7.0 7.0>
         rotate <-30.0 30.0 0.0>
         quick_color Red
      }
      finish {
         ambient 0.3
         diffuse 0.7
         phong 0.5
         phong_size 10.0
      }
   }
}

/* Place the garden globe on left side of pool */
object { Garden_Globe translate <-60.0, 0.0, 0.0> }

/* The hedge behind the pool */
object {
   Cube

   scale <200.0, 30.0, 30.0>
   translate <-100.0, 0.0, 180.0>

   texture {
      pigment {
         spotted
         turbulence 0.5
         colour_map {
            [0.00 0.25  colour YellowGreen colour Green ]
            [0.25 0.75  colour Green colour DarkGreen]
            [0.75 1.001 colour DarkGreen colour YellowGreen ]
         }
         quick_color YellowGreen
      }
      normal { wrinkles 1.0 }
      finish { crand 0.05 }
      scale <10.0, 10.0, 20.0>
   }
}

/* The hedge on the right side of pool */
object {
   Cube

   scale <30.0, 30.0, 100.0>
   translate <100.0, 0.0, -85.0>

   texture {
      pigment {
         spotted
         turbulence 0.5
         colour_map {
            [0.00 0.25  colour YellowGreen colour Green ]
            [0.25 0.75  colour Green colour DarkGreen]
            [0.75 1.001 colour DarkGreen colour YellowGreen ]
         }
         quick_color YellowGreen
      }
      normal { wrinkles 1.0 }
      finish { crand 0.05 }
      scale <10.0, 10.0, 20.0>
   }
}

/* a low, squat shrub of some generic species */
sphere {
   <0, 0, 0>, 1

   scale <30.0, 20.0, 25.0>
   translate <-70.0, 0.0, 110.0>

   texture {
      pigment {
         spotted
         turbulence 0.5
         colour_map {
            [0.00 0.25  colour Khaki colour Green ]
            [0.25 0.50  colour Green colour DarkGreen]
            [0.50 0.75  colour DarkGreen colour MediumForestGreen]
            [0.75 1.001 colour MediumForestGreen colour YellowGreen ]
         }
         quick_color YellowGreen
      }
      normal { wrinkles 1.0 }
      finish { crand 0.05 }
      scale 5.0
   }
}
