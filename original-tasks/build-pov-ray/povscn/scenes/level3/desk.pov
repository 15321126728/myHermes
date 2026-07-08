// Persistence Of Vision raytracer version 2.0 sample file.

// By  Tom Price
// Requires "rough.gif" 320x200x256, but feel free to substitute any
// image that you wish.  (It goes in a picture frame on the desk)

#include "shapes.inc"
#include "colors.inc"
#include "textures.inc"

#declare
RedPencil = union {
   intersection {
      object { Cylinder_Y scale <0.5, 1.0, 0.5> }
      plane { y, 30.0 }
      plane { y, 0.0 inverse }

      finish {
         crand 0.05
         ambient 0.3
         diffuse 0.7
      }
      pigment { Red }
   }

   intersection {
      object { Cylinder_Y scale <0.5, 1.0, 0.5> }
      plane { y, 32.0 }
      plane { y, 30.0 inverse }

      finish {
         crand 0.05
         ambient 0.3
         diffuse 0.7
      }
      pigment { Tan }
   }
}

#declare
GreenPencil = union {
   intersection {
      object { Cylinder_Y scale <0.5, 1.0, 0.5> }
      plane { y, 30.0 }
      plane { y, 0.0 inverse }

      finish {
         crand 0.05
         ambient 0.3
         diffuse 0.7
      }
      pigment { Green }
   }

   intersection {
      object { Cylinder_Y scale <0.5, 1.0, 0.5> }
      plane { y, 32.0 }
      plane { y, 30.0 inverse }

      finish {
         crand 0.05
         ambient 0.3
         diffuse 0.7
      }
      pigment { Tan }
   }
}

#declare
BluePencil = union {
   intersection {
      object { Cylinder_Y scale <0.5, 1.0, 0.5> }
      plane { y, 30.0 }
      plane { y, 0.0 inverse }

      finish {
         crand 0.05
         ambient 0.3
         diffuse 0.7
      }
      pigment { Blue }
   }
   intersection {
      object { Cylinder_Y scale <0.5, 1.0, 0.5> }
      plane { y, 32.0 }
      plane { y, 30.0 inverse }

      finish {
         crand 0.05
         ambient 0.3
         diffuse 0.7
      }
      pigment { Tan }
   }
}

camera {
   location <0.0, 40.0, -150.0>
   up <0.0, 1.0, 0.0>
   right <4/3, 0.0, 0.0>
   look_at <0.0, 0.0, 0.0>
}

/*The back wall*/

plane { z, 200.0
   finish {
      crand 0.1
      ambient 0.3
      diffuse 0.7
   }
   pigment { LightGray }
}

/*The ceiling*/
plane { y,  500.0
   finish {
      crand 0.1
      ambient 0.3
      diffuse 0.7
   }
   pigment { White }
}


/*The desk surface*/
intersection {
   plane { y,    2.0 }
   plane { y,   -2.0 inverse }
   plane { z,  100.0 }
   plane { z, -100.0 inverse }
   plane { x,  125.0 }
   plane { x, -125.0 inverse }

   translate -20.0*y

   finish {
      crand 0.05
      ambient 0.4
      diffuse 0.6
      reflection 0.2
      brilliance 3.0
   }
   pigment {
      Dark_Wood
      scale <5.0, 1.0, 1.0>
   }
}

/*Paperwork*/
union {
   triangle {
      <0.0, 0.0, 0.0>
      <8.5, 0.0, 0.0>
      <0.0, 0.0, -11.0>
   }
   triangle {
      <0.0, 0.0, -11.0>
      <8.5, 0.0, -11.0>
      <8.5, 0.0, 0.0>
   }

   scale <3.0, 1.0, 3.0>
   rotate -30.0*y
   translate <-20.0, -17.9, -40.0>

   finish {
      crand 0.05
      ambient 0.1
      diffuse 0.4
   }
   pigment { colour red 0.5 green 0.5 blue 0.3 }
}

/*a glass paperweight*/
intersection {
   sphere { <0.0, -5.0, 0.0>, 10.0 }
   plane { y, 0.0 inverse }

   translate <0.0, -17.8, -35.0>

   finish {
      ambient 0.1
      diffuse 0.6
      reflection 0.1
      refraction 1.0
      ior 1.5
      brilliance 2.0
   }
   pigment { colour red 0.3 green 0.5 blue 0.3 filter 1.0 }
}

/*The desk lamp*/

union {
   object {
      intersection {
         object { Cylinder_Y scale <3.0, 1.0, 3.0> }
         plane { y, 40.0 }
         plane { y, -18.0 inverse }
      }

      finish {
         Shiny
         crand 0.05
         ambient 0.2
         diffuse 0.7
      }
      pigment { colour red 0.7 green 0.6 blue 0.1 }
   }

   intersection {
      object { Cylinder_Y scale <25.0, 1.0, 25.0> }
      plane { y, 2.0 }
      plane { y, -2.0 inverse }

      translate <0.0, -16.0, -5.0>

      finish {
         crand 0.05
         ambient 0.3
         diffuse 0.6
         reflection 0.4
         brilliance 4.0
      }
      normal { bumps 0.1 }
      pigment { colour red 0.5 green 0.4 blue 0.1 }
   }

   intersection {
      object { Cylinder_X scale <1.0, 10.0, 10.0> }
      object { Cylinder_X scale <1.0, 9.95, 9.95> inverse }
      plane { y, 0.0 inverse }
      plane { x, -30.0 inverse }
      plane { x, 30.0 }

      translate <0.0, 35.0, -13.0>

      finish {
         Shiny
         crand 0.05
         ambient 0.5
         diffuse 0.5
         reflection 0.3
         brilliance 4.0
      }
      pigment { DarkGreen }
   }

   union {
      intersection {
         sphere { <-30.0, 35.0, -13.0>, 10.0 }
         sphere { <-30.0, 35.0, -13.0>, 9.95 inverse }
         plane { y, 35.0 inverse }
         plane { x, -30.0 }
      }
      intersection {
         plane { y, 35.0 inverse }
         plane { x, 30.0 inverse }
         sphere { <30.0, 35.0, -13.0>, 10.0 }
         sphere { <30.0, 35.0, -13.0>, 9.95 inverse }
      }

      finish {
         Shiny
         crand 0.05
         ambient 0.2
         diffuse 0.7
      }
      pigment { colour red 0.7 green 0.6 blue 0.1 }
   }

   rotate 35*y
   translate <50.0, 0.0, 30.0>
}

/*The fluorescent tube inside the lamp*/

light_source {
    <0, 0, 0> color White

    looks_like {
       intersection {
          object { Cylinder_X }
          plane { x, -25.0 inverse }
          plane { x,  25.0 }

          pigment { White }
          finish { ambient 1 diffuse 0 }
      }
   }

   translate <0.0, 43.0, -10.0>
   rotate 35*y
   translate <50.0, 0.0, 30.0>
}

/*The Picture itself*/

union {
   intersection {
      plane { x,  1.0 }
      plane { x, -1.0 inverse }
      plane { y,  1.0 }
      plane { y, -1.0 inverse }
      plane { z,  1.0 }
      plane { z, -1.0 inverse }

      translate <1.0, 1.0, 1.0>
      scale <20.0, 15.0, 1.0>

      finish {
         ambient 0.05
         diffuse 0.9
      }
      pigment {
         image_map { gif "rough.gif" once interpolate 2.0 }
         scale <40.0, 30.0, 1.0>
         scale <1.5, 1.5, 1.0>
      }
   }

   /* The picture frame */
   union {
      intersection {
         union {
            object { Cylinder_Y translate 41*x }
            object { Cylinder_Y translate -1*x }
         }
         plane { y, 31.0 }
         plane { y, -1.0 inverse }
      }
      intersection {
         union {
            object { Cylinder_X translate 31*y }
            object { Cylinder_X translate -1*y }
         }
         plane { x, 41.0 }
         plane { x, -1.0 inverse }
      }
      sphere { <-1.0, -1.0, 0.0>, 1.0 }
      sphere { <-1.0, 31.0, 0.0>, 1.0 }
      sphere { <41.0, -1.0, 0.0>, 1.0 }
      sphere { <41.0, 31.0, 0.0>, 1.0 }

      finish {
         Shiny
         crand 0.05
         ambient 0.3
         diffuse 0.7
      }
      pigment { colour red 0.6 green 0.5 blue 0.1 }
   }

   scale 1.5
   rotate <10.0, -35.0, 0.0>
   translate <-65.0, -15.0, -25.0>
}

/*The pencil holder*/
union {
   intersection {
      object { Cylinder_Y scale <5.0, 1.0, 5.0> }
      object { Cylinder_Y scale <4.8, 1.0, 4.8> inverse }
      plane { y, 0.0 inverse }
      plane { y, 15.0 rotate -45*x }

      finish {
         Shiny
         crand 0.05
         ambient 0.3
         diffuse 0.7
         reflection 0.4
         brilliance 6.0
      }
      pigment { colour red 0.7 green 0.6 blue 0.1 }
   }
   object {
      RedPencil
      rotate -2*z
      translate <1.0, 0.0, 1.0>
   }
   object {
      GreenPencil
      rotate 2.0*z
      translate <-1.0, 3.0, 0.0>
   }
   object { 
      BluePencil
      rotate <-2.0, 0.0, 3.0>
      translate <0.0, -2.0, -1.0>
   }

   bounded_by {
      intersection {
         object { Cylinder_Y scale <6.0, 1.0, 6.0> }
         plane { y, 36.0 }
         plane { y, -4.0 inverse }
      }
   }

   rotate 45*y
   translate <70.0, -18.0, -20.0>
}

/*The light source*/

light_source { <20.0, 100.0, -200.0> colour White }
