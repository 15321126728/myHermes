// Persistence Of Vision raytracer version 2.0 sample file.

// piece I: 
//          by Truman Brown 11/91
//          Close-up of a museum piece in the Woild Museum

// The lighting is intentionally dim when the image is rendered.
// You can enhance the image using PicLab's gamma, brightness, and
// contrast command when you post-process the image.

#include "colors.inc"
#include "textures.inc"
#include "shapes.inc"

camera {
   location  <-36.0, 29.0, -70.0>
   direction <  0.0,  0.0,  2.0  >
   up        <  0.2,  0.8,  0.0  >
   right     <  4/3,  0.0,  0.0  >
   look_at   <  0.0, -8.0,  0.0  >
}

// ----------------------------------------------------------------------------
// lights
// ----------------------------------------------------------------------------
#declare Light1c =  color red 0.1 green 0.1 blue 0.1
#declare Light2c =  color red 0.2 green 0.2 blue 0.2
#declare Light3c =  color red 0.3 green 0.3 blue 0.3
#declare Light4c =  color red 0.4 green 0.4 blue 0.4
#declare Light5c =  color red 0.5 green 0.5 blue 0.5

#declare light1 = light_source { <0.0, 0.0, 0.0>  color Light1c }
#declare light2 = light_source { <0.0, 0.0, 0.0>  color Light2c }
#declare light3 = light_source { <0.0, 0.0, 0.0>  color Light3c }
#declare light4 = light_source { <0.0, 0.0, 0.0>  color Light4c }
#declare light5 = light_source { <0.0, 0.0, 0.0>  color Light5c }

union {
   object { light1 translate <  35,  30, -16> }
   object { light3 translate < -25,  40,  20> }
   object { light2 translate < -48,  30, -20> }
   object { light5 translate <  20, -10, -22> }
   pigment { White }
}

// ----------------------------------------------------------------------------
// textures
// ----------------------------------------------------------------------------
#declare rod_texture1 =
texture {
   pigment { Firebrick }
   finish {
      specular 0.9
      roughness 0.001
      ambient 0.0
      diffuse 0.5
      reflection 0.25
   }
}

#declare loop_texture =
texture {
   pigment { Black }
   finish {
      ambient 0.01
      diffuse 0.45
      specular 1.00
      roughness 0.001
      reflection 0.4
   }
}

#declare innertube_texture =
texture {
   pigment { SteelBlue }
   finish {
      ambient 0.05
      diffuse 0.1
      specular 1.00
      roughness 0.001
      reflection 0.90
   }
}

#declare balls_texture =
texture {
   pigment { White }
   finish {
      ambient 0.01
      diffuse 0.3
      specular 1.00
      roughness 0.001
      reflection 0.85
   }
}

#declare tile1_texture =
texture {
   pigment {
      wood
      turbulence 0.5
      color_map {
         [0.0 0.7  color red 0.93 green 0.710 blue 0.532
         color red 0.98 green 0.810 blue 0.600]
         [0.7 1.01 color red 0.60 green 0.333 blue 0.266
         color red 0.70 green 0.600 blue 0.23]
      }
      rotate 90*y
      scale 5
   }
   finish {
      crand 0.05
      specular 1.0
      roughness 0.001
      ambient 0.05
      diffuse 0.35
      reflection 0.15
   }
}

#declare tile2_texture =
texture {
   pigment {
      wood
      turbulence 0.6
      color_map {
         [0.0 0.8  color red 0.42857 green 0.23810 blue 0.04762
         color red 0.42857 green 0.23810 blue 0.04762]
         [0.8 1.01 color red 0.4     green 0.333   blue 0.066
         color red 0.2     green 0.033   blue 0.033]
      }
      scale 7
   }
   finish {
      crand 0.05
      specular 1.0
      roughness 0.001
      ambient 0.01
      diffuse 0.75
      reflection 0.15
   }
}

#declare frame_texture =
texture {
   Bronze_Texture
   finish {
      specular 1.0
      roughness 0.001
      ambient 0.11
      diffuse 0.8
      reflection 0.85
   }
}

// ----------------------------------------------------------------------------
// torus primatives
// ----------------------------------------------------------------------------
#declare torus1 =
quartic { <
   1.0, 0.0,   0.0,  0.0,   2.0,      /* major radius: 5.0 */
   0.0, 0.0,   2.0,  0.0, -50.5,      /* minor radius: 0.5 */
   0.0, 0.0,   0.0,  0.0,   0.0,      /* outer radius: 5.5 */
   0.0, 0.0,   0.0,  0.0,   0.0,      /* inner radius: 4.5 */
   1.0, 0.0,   0.0,  2.0,   0.0,
   49.5, 0.0,   0.0,  0.0,   0.0,
   1.0, 0.0, -50.50, 0.0, 612.5625 >
}

#declare torus2=
quartic { <
   1.0, 0.0,  0.0,  0.0,  2.0,        /* major radius: 0.8 */
   0.0, 0.0,  2.0,  0.0, -1.36,       /* minor radius: 0.2 */
   0.0, 0.0,  0.0,  0.0,  0.0,        /* outer radius: 1.0 */
   0.0, 0.0,  0.0,  0.0,  0.0,        /* inner radius: 0.6 */
   1.0, 0.0,  0.0,  2.0,  0.0,
   1.2, 0.0,  0.0,  0.0,  0.0,
   1.0, 0.0, -1.36, 0.0,  0.36 >
}

#declare torus3 =
quartic { <
   1.0, 0.0,    0.0, 0.0,     2.0,     /* major radius: 12.0 */
   0.0, 0.0,    2.0, 0.0,  -296.0,     /* minor radius:  2.0 */
   0.0, 0.0,    0.0, 0.0,     0.0,     /* outer radius: 14.0 */
   0.0, 0.0,    0.0, 0.0,     0.0,     /* inner radius: 10.0 */
   1.0, 0.0,    0.0, 2.0,     0.0,
   280.0, 0.0,    0.0, 0.0,     0.0,
   1.0, 0.0, -296.0, 0.0, 19600.0 >
}

#declare torus4 =
quartic { <
   1.0, 0.0,   0.0, 0.0,    2.0,       /* major radius: 7.0 */
   0.0, 0.0,   2.0, 0.0,  -98.5,       /* minor radius: 0.5 */
   0.0, 0.0,   0.0, 0.0,    0.0,       /* outer radius: 7.5 */
   0.0, 0.0,   0.0, 0.0,    0.0,       /* inner radius: 6.5 */
   1.0, 0.0,   0.0, 2.0,    0.0,
   97.5, 0.0,   0.0, 0.0,    0.0,
   1.0, 0.0, -98.5, 0.0, 2376.5625 >
}

// ----------------------------------------------------------------------------
// piece definitions
// ----------------------------------------------------------------------------
#declare halfring =
object {
   torus1
   rotate 90*x
   clipped_by {
      plane { -y, 0 }
   }
   texture { rod_texture1 }
   bounded_by {
      sphere { <0, 0, 0>, 5.51  }
   }
   translate -12*x
}

#declare halfring_array =
union {
   object { halfring rotate  -10*y  }
   object { halfring rotate  -40*y  }
   object { halfring rotate -100*y  }
   object { halfring rotate -130*y  }
   object { halfring rotate -190*y  }
   object { halfring rotate -220*y  }
   object { halfring rotate -280*y  }
   object { halfring rotate -310*y  }

   bounded_by {
      sphere { <0, 0, 0>, 17.51 }
   }
}

#declare quarterring =
object {
   torus1
   rotate 90*x
   clipped_by {
      plane { y, 0  }
      plane { x, 0  }
   }
   texture {
      rod_texture1
   }
   bounded_by {
      sphere { <-2.75, -2.75, 0>, 3.9  }
   }
   translate <-12, 0, 0>
}

#declare quarterring_array =
union {
   object { quarterring rotate  -10*y  }
   object { quarterring rotate  -40*y  }
   object { quarterring rotate -100*y  }
   object { quarterring rotate -130*y  }
   object { quarterring rotate -190*y  }
   object { quarterring rotate -220*y  }
   object { quarterring rotate -280*y  }
   object { quarterring rotate -310*y  }
   bounded_by {
      sphere { <0, 0, 0>, 17.51  }
   }
}

#declare ringball =
sphere {
   <0, -5.0, 0>, 1.0
   texture {
      rod_texture1
   }
   translate <-12, 0, 0>
}

#declare ringball_array =
union {
   object { ringball rotate  -10*y  }
   object { ringball rotate  -40*y  }
   object { ringball rotate -100*y  }
   object { ringball rotate -130*y  }
   object { ringball rotate -190*y  }
   object { ringball rotate -220*y  }
   object { ringball rotate -280*y  }
   object { ringball rotate -310*y  }
   bounded_by {
      sphere { <0, 0, 0>, 13.5  }
   }
}

#declare pole =
object {
   Disk_Y
   rotate 180*x
   scale <0.5, 20, 0.5>
   translate <5, 0, 0>

   texture {
      rod_texture1
   }
   translate <-12, 0, 0>
}

#declare pole_array =
union {
   object { pole rotate  -10*y  }
   object { pole rotate  -40*y  }
   object { pole rotate -100*y  }
   object { pole rotate -130*y  }
   object { pole rotate -190*y  }
   object { pole rotate -220*y  }
   object { pole rotate -280*y  }
   object { pole rotate -310*y  }
   bounded_by {
      sphere { <0, -10, 0>, 13.5  }
   }
}

#declare blueloop =
object {
   torus2
   rotate 90*z
   texture {
      loop_texture
   }
   bounded_by {
      sphere { <0, 0, 0>, 1.1 }
   }
}

#declare blueloop_set =
union {
   object { blueloop translate 5*y rotate 0*z  }
   object { blueloop translate 5*y rotate +90*z  }
   object { blueloop translate 5*y rotate -90*z  }
   bounded_by {
      sphere { <0, 0, 0>, 6.51  }
   }
   translate -12*x
}

#declare blueloop_array =
union {
   object { blueloop_set rotate  -10*y  }
   object { blueloop_set rotate  -40*y  }
   object { blueloop_set rotate -100*y  }
   object { blueloop_set rotate -130*y  }
   object { blueloop_set rotate -190*y  }
   object { blueloop_set rotate -220*y  }
   object { blueloop_set rotate -280*y  }
   object { blueloop_set rotate -310*y  }
   bounded_by {
      sphere { <0, 0, 0>, 18.51 }
   }
}

#declare basering =
object {
   torus4
   texture {
      rod_texture1
   }
   bounded_by {
      sphere { <0, 0, 0>, 7.6 }
   }
   translate <0, -20.5, 0>
}

#declare innertube =
object {
   torus3
   texture {
      innertube_texture
   }
   bounded_by {
      sphere { <0, 0, 0>, 14.1 }
   }
}

#declare structurebase =
union {
   object { halfring_array     }
   object { quarterring_array  }
   object { ringball_array     }
   object { blueloop_array     }
   object { pole_array         }
   object { basering   }
   object { innertube  }
   bounded_by {
      sphere { <0, 0, 0>, 22  }
   }
}

#declare balls =
sphere {
   <0, 0, 0>, 4.0
   texture {
      balls_texture
   }
}

#declare block1 =
intersection {
   object {
      Cube
      scale <10, 1, 10>
   }
   object {
      Cylinder_Y
      scale <6, 1, 6>
      inverse
   }

   texture {
      tile1_texture
   }
   bounded_by {
      sphere { <0, 0, 0>, 15 }
   }
}

#declare block2 =
intersection {
   object {
      Cube
      scale <10, 1, 10>
   }
   object {
      Cylinder_Y
      scale <6, 1 ,6>
      inverse
   }

   texture {
      tile2_texture
   }
   bounded_by {
      sphere { <0, 0, 0>, 15 }
   }
}

#declare frame =
object {
   Cube
   scale <21, 1.5, 21>

   clipped_by {
      object {
         Cube
         scale <20, 2, 20>
         inverse
      }
   }
   texture { frame_texture  }
}

#declare bigtile =
union {
   object { block1 translate < 10, -1,  10>  }
   object { block1 translate <-10, -1, -10>  }
   object { block2 translate <-10, -1,  10>  }
   object { block2 translate < 10, -1, -10>  }
   object { frame  }

   bounded_by { box { <-21.1, -2.6, -21.1>, <21.1, 0.6, 21.1> } }
}

#declare floor =
object { bigtile }

// color debugger
// object { Cylinder_Y scale <3, 1, 3> texture { rod_texture1 } }
// object { Cylinder_X scale <1, 3, 3> texture { rod_texture1 } }

//-----------------------------------------------------------------------------
// Put it all together and render it
//-----------------------------------------------------------------------------
object { structurebase  }

union {
   object { balls translate <0,  0, 0> }
   object { balls translate <0, -8, 0> }
   object { balls translate <0, -16, 0> }

   bounded_by {
      object {
         Cylinder_Y
         scale <4.1, 1, 4.1>
      }
   }
}

object {
   floor
   rotate 45*y
   translate -20*y
}
