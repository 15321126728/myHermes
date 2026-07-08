// Persistence Of Vision raytracer version 2.0 sample file.

// By Tom Price

#include "shapes.inc"
#include "colors.inc"
#include "textures.inc"

camera {
   location <0.0, 0.0, -100.0>
   up <0.0, 1.0, 0.0>
   right <4/3, 0.0, 0.0>
   look_at <0.0, 11.547005, 0.0>
}

/*The Kaleidoscope Tube*/
union {
   union {
      union {
         triangle {
            <0.0,  1.1547005, -100.0>
            <0.0,  1.1547005,  0.0>
            <-1.0, -0.5773502, 0.0>
         }

         triangle {
            <0.0,  1.1547005, -100.0>
            <-1.0, -0.5773502, -100.0>
            <-1.0, -0.5773502, 0.0>
         }

         texture {
            pigment { White }
            finish {
               crand 0.05
               ambient 0.1
               diffuse 0.7
               reflection 1.0
            }
         }
      }

      union {
         triangle {
            <-0.001, 1.1547005, -100.0>
            <-0.001, 1.1547005,  0.0>
            <1.0, -0.5773502,  0.0>
         }

         triangle {
            <-0.001, 1.1547005, -100.0>
            <1.0, -0.5773502, -100.0>
            <1.0, -0.5773502, 0.0>
         }

         texture {
            pigment { White }
            finish {
               crand 0.05
               ambient 0.1
               diffuse 0.7
               reflection 1.0
            }
         }
      }

      union {
         triangle {
            <-1.0, -0.5773502, -100.0>
            <1.0,  -0.5773502, -100.0>
            <-1.0, -0.5773502, 0.0>
         }

         triangle {
            <1.0, -0.5773502, -100.0>
            <-1.0, -0.5773502, 0.0>
            <1.0, -0.5773502, 0.0>
         }

         texture {
            pigment { Bright_Blue_Sky }
            finish {
               crand 0.05
               ambient 0.5
               diffuse 0.5
            }
         }
      }

      triangle {
         <-1.0, -0.5773502, 0.0>
         <1.0, -0.5773502, 0.0>
         <0.0,  1.1547005,  0.0>

         texture {
            pigment { colour red 0.5 green 0.5 blue 0.5 filter 0.3 }
            finish {
               crand 0.1
               ambient 0.3
               diffuse 0.7
            }
         }
      }

      scale <10.0, 10.0, 1.0>
   }

   sphere {
      <-3.5, -3.0, -45.0>, 3.0

      texture {
         pigment { Red filter 0.8 }
         finish {
            crand 0.05
            ambient 0.1
            diffuse 0.7
            reflection 0.2 
            refraction 1.0
            ior 1.2
            brilliance 3.0
         }
      }
   }

   sphere {
      <4.0, -3.0, -40.0>, 2.5

      texture {
         pigment { Green filter 0.8 }
         finish {
            crand 0.05
            ambient 0.1
            diffuse 0.7
            reflection 0.2 
            refraction 1.0
            ior 1.2
            brilliance 3.0
         }
      }
   }

   sphere {
      <0.0, 4.0, -30.0>, 2.0
      texture {
         pigment { Magenta filter 0.8 }
         finish {
            crand 0.05
            ambient 0.1
            diffuse 0.7
            reflection 0.2 
            refraction 1.0
            ior 1.2
            brilliance 3.0
         }
      }
   }

   sphere {
      <0.0, -2.0, -20.0>, 2.0

      texture {
         pigment { Yellow filter 0.8 }
         finish {
            crand 0.05
            ambient 0.1
            diffuse 0.7
            reflection 0.2 
            refraction 1.0
            ior 1.2
            brilliance 3.0
         }
      }
   }

   sphere {
      <2.0, -4.0, -70.0>, 2.0
      texture {
         pigment { Cyan filter 0.8 }
         finish {
            crand 0.05
            ambient 0.1
            diffuse 0.7
            reflection 0.2 
            refraction 1.0
            ior 1.2
            brilliance 3.0
         }
      }
   }

   triangle {
      <-1.0, -8.0, -50.0>
      < 0.0,  1.0, -50.0>
      < 2.0, -3.0, -50.0>

      texture {
         pigment { colour red 0.8 green 0.5 blue 0.3 filter 0.9 }
         finish {
            crand 0.05
            ambient 0.3
            diffuse 0.7
         }
      }
   }

   triangle {
      <1.0, 7.0, -5.0>
      < -4.0,  -1.0, -5.0>
      < 3.0, 1.0, -5.0>

      texture {
         pigment { colour red 0.2 green 0.9 blue 0.5 filter 0.9 }
         finish {
            crand 0.05
            ambient 0.3
            diffuse 0.7
         }
      }
   }

   triangle {
      <-8.0, -5.0, -80.0>
      < -4.0,  -1.0, -80.0>
      < 0.0, -4.0, -80.0>

      texture {
         pigment { colour red 0.7 green 0.7 blue 0.3 filter 1.0 }
         finish {
            crand 0.05
            ambient 0.3
            diffuse 0.7
            refraction 0.9
            ior 1.0
         }
      }
   }

   union {
      triangle {
         <0.0, 0.0, 0.0>
         <0.0, 1.0, 0.0>
         <1.0, 0.0, 0.0>
      }

      triangle {
         <1.0, 0.0, 0.0>
         <0.0, 1.0, 0.0>
         <1.0, 1.0, 0.0>
      }

      rotate <20.0, 45.0, -10.0>
      translate <-0.6, -0.5, -65.0>
      scale <10.0, 10.0, 1.0>

      texture {
         // Subsitute your own image here instead of sunset.ham
         //    image_map { <1.0 -1.0 0.0> iff "sunset.ham" once 
         //    interpolate 2.0
         //    }
         pigment {
            Black
            rotate <20.0, 45.0, -10.0>
            translate <-0.6, -0.5, -65.0>
            scale <9.0, 9.0, 1.0>
         }
         finish {
            ambient 0.5
            diffuse 0.3  
            refraction 0.25
            ior 1.0
         }
      }
   }
}

light_source { <0.0, 0.0, 20.0> colour White }
