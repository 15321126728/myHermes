// Persistence Of Vision raytracer version 2.0 sample file.

// By Tom Price


#include "shapes.inc"
#include "colors.inc"
#include "textures.inc"

camera {
   location <0.0, 35.0, -150.0>
   up <0.0, 1.0, 0.0>
   right <4/3, 0.0, 0.0>
   look_at <0.0, 0.0, 0.0>
}

/*The floor*/
plane { y, -60.0
   pigment {
      checker colour Brown colour LightGray
      quick_colour red 0.4 blue 0.4 green 0.4
      scale 40.0
   }
   finish {
      crand 0.05 
      ambient 0.1
      diffuse 0.7
      reflection 0.4
      phong 1.0
      phong_size 20.0
   }
}

/*The Sky*/
sphere { <0.0, -40000.0, 0.0>, 50000.0
   pigment {
      Bright_Blue_Sky
      quick_colour Blue
      scale <8000.0, 3000.0, 3000.0>
   }
   finish {
      crand 0.05 
      ambient 0.7
      diffuse 0.0
   }
}

union {
   intersection {
      sphere { <0, 0, 0>, 40 }
      object { Cylinder_Z scale <20, 20, 1> inverse }

      pigment { colour red 0.6 green 0.6 blue 0.0 }
      finish {
         crand 0.05
         ambient 0.1
         diffuse 0.7
         reflection 0.7
         brilliance 6.0
         specular 0.5
      }
   }

   union {
      triangle {
         <-1.0, 0.0, -0.5773502>
         < 1.0, 0.0, -0.5773502>
         < 0.0, 0.0,  1.1547005>

         pigment { Gold }
         finish {
            crand 0.05
            ambient 0.1
            diffuse 0.7
            reflection 0.4
            brilliance 6.0
         }
      }

      triangle {
         <-1.0, 0.0, -0.5773502>
         < 0.0, 0.0,  1.1547005>
         < 0.0, 1.6329931,  0.0>

         pigment { Gold }
         finish {
            crand 0.05
            ambient 0.1
            diffuse 0.7
            reflection 0.4
            brilliance 6.0
         }
      }

      triangle {
         <1.0, 0.0, -0.5773502>
         <0.0, 0.0,  1.1547005>
         <0.0, 1.6329931,  0.0>

         pigment { Gold }
         finish {
            crand 0.05
            ambient 0.1
            diffuse 0.7
            reflection 0.4
            brilliance 6.0
         }
      }

      triangle {
         <-1.0, 0.0, -0.5773502>
         < 1.0, 0.0, -0.5773502>
         < 0.0, 1.6329931,  0.0>

         pigment { colour red 0.5 green 0.4 blue 0.0 }
         finish {
            crand 0.05
            ambient 0.4
            diffuse 0.6
            reflection 0.2
            brilliance 6.0
         }
      }

      translate -0.4082886*y
      scale 15
      rotate <-45.0, -50.0, 10.0>
   }

   intersection {
      object { Cylinder_Y scale <7.0, 1.0, 7.0> }
      plane { y, -20.0 }

      pigment {
         Pine_Wood
         scale <10.0, 100.0, 10.0>
      }
      finish {
         crand 0.05
         ambient 0.1
         diffuse 0.7
         reflection 0.5
         specular 0.5
      }
   }

   translate <10.0, 20.0, 60.0>
}

union {
   sphere { <0.0, 0.0, 0.0>, 20.0
      texture {
         Glass
         finish { crand 0.05 }
      }
   }          

   intersection {
      object { Cylinder_Y scale <3.0, 1.0, 3.0> }
      plane { y, 0.0 }

      pigment {
         Pine_Wood
         scale <10.0, 50.0, 10.0>
      }
      finish {
         crand 0.05
         ambient 0.1
         diffuse 0.7
         reflection 0.5
         specular 0.5
      }
   }

   translate <-40.0, 15.0, -10.0>
}

union {
   sphere { <0.0, 0.0, 0.0>, 15.0
      pigment { colour red 0.0 green 0.6 blue 0.3 }
      finish {
         crand 0.05
         ambient 0.1
         diffuse 0.5
         reflection 0.5
         brilliance 3.0
         specular 0.1
      }
   }

   intersection {
      object { Cylinder_Y scale <3.0, 1.0, 3.0> }
      plane { y, 0.0 }

      pigment {
         Pine_Wood
         scale <10.0, 100.0, 10.0>
      }
      finish {
         crand 0.05
         ambient 0.1
         diffuse 0.7
         reflection 0.5
         specular 0.5
      }
   }

   translate <50.0, 10.0, -30>
}

light_source { <-100.0, 100.0, -200.0> colour White }

