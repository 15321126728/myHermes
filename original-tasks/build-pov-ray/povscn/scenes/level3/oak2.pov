// Persistence Of Vision Raytracer version 2.0 sample file.

// Scene file by Dan Farmer    November, 1991
//
// note: To properly process on a pc, the resultant .gif file should
// be modified with piclab: brighten 20 contrast 45, gamma 0.6, transform
//
// Many of the declarations here are not the same as in the #include files!
//=========================================================================
#include "colors.inc"
#include "shapes.inc"
#include "textures.inc"

#declare BlueViolet     = color red 0.38 green 0.39 blue 0.58 // tce designed color
#declare DarkPurple     = color red 0.53 green 0.12 blue 0.47
#declare CoolCopper     = color red 0.85 green 0.53 blue 0.10
#declare LightWood      = color red 0.91 green 0.76 blue 0.65
#declare MediumWood     = color red 0.65 green 0.50 blue 0.39
#declare DarkWood       = color red 0.52 green 0.37 blue 0.26
#declare SemiSweetChoc  = color red 0.42 green 0.26 blue 0.15
#declare BakersChoc     = color red 0.36 green 0.20 blue 0.09
#declare VeryDarkBrown  = color red 0.35 green 0.00 blue 0.14

// a unit sphere is one with radius of 1.0.
// This shape is equivilent in size to a unit sphere {
// and will scale evenly in all directions.

#declare Torus = torus { 1.0, 0.25 }

#declare LeftTopElbow = object {
   Torus
   rotate 90*x

   clipped_by {
      plane { x, 0 }
      plane { -y, 0 }
   }
   texture { Copper_Texture pigment { quick_color Red } }
}

#declare RightTopElbow = object {
   Torus
   rotate 90*x

   clipped_by {
      plane { -x, 0 }
      plane { -y, 0 }
   }
   texture { Copper_Texture pigment { quick_color Red } }
}

#declare XTube = cylinder {
   -x, x, 1
   texture { Copper_Texture pigment { quick_color Red } }
}

#declare YTube = cylinder {
   -y, y, 1
   texture { Copper_Texture pigment { quick_color Red } }
}

camera {
   location <20, 15, -35>
   direction <0, 0, 1.2>
   up  <0, 1, 0>
   right <4/3, 0, 0>
   look_at <1.5, 5, 0>
}

#declare Light = color red 0.75 green 0.75 blue 0.75

light_source { <-30, 500, -1.0> colour Light }

light_source { <-5, 30, -50> colour Light }

/* floor */
plane {
   y, -6
 
   pigment {
      granite
      color_map { [0.0 1.01 color BlueViolet color DarkPurple] }
      quick_color White
   }
   finish {
      reflection 0.15
      ambient 0.075  diffuse 0.5
   }
}

#declare Oak =  pigment {
   wood
   turbulence 0.05
   colour_map {
      [0.00 0.10 color SemiSweetChoc color SemiSweetChoc]
      [0.10 0.90 color SemiSweetChoc color DarkWood]
      [0.90 1.01  color DarkWood  color DarkWood ]
   }
}

#declare WoodSphere = sphere {
   <0, 0, 0>, 10

   texture {
      pigment {
         Oak
         scale <0.5, 0.5, 1.0>
         translate <0.25, 0.05, 0.5>
         rotate <0, 0, 0.5>
         quick_color White
      }
      finish {
         Shiny
         reflection 0.12
         ambient 0.075
         diffuse 0.7
      }
   }

   texture {
      finish {
         Shiny
         ambient 0.075 diffuse 0.7
      }
      pigment { Clear }
   }
}

#declare Chamfer = union {
   object { Disk_X scale <12.5, 0.65, 0.65> translate <0, 0, -12> }
   object { Disk_X scale <12.5, 0.65, 0.65> translate <0, 0, 12>  }
   object { Disk_Z scale <0.65, 0.65, 12.5> translate <-12, 0, 0> }
   object { Disk_Z scale <0.65, 0.65, 12.5> translate <12, 0, 0> }
}

#declare BrassBall = sphere {
   <0, 0, 0>, 1.5
   texture { Brass_Texture pigment { quick_color Red } }
}

#declare Railing = union {
   object { LeftTopElbow  translate <-8, 0, 0> }
   object { RightTopElbow translate <+8, 0, 0> }
   object { XTube  scale <8.0, 0.25, 0.25>  translate <0, 1, 0>  }
   object { YTube  scale <0.25, 2, 0.25>    translate <+9, -2, 0> }
   object { YTube  scale <0.25, 2, 0.25>    translate <-9, -2, 0> }
}

#declare Base = difference {
   object { Cube scale <12, 2, 12> }
   object { Chamfer translate <0, 2, 0> }

   texture {
      pigment {
         Oak
         scale <0.45, 0.45, 0.7>
         rotate <0.20, 0.10, 0.05>
         translate <0, -1, 0>
         quick_color Red
      }
      finish {
         Shiny
         reflection 0.15
         ambient 0.075 diffuse 0.7
      }
   }

   texture {
      finish {
         Shiny
         ambient 0.075 diffuse 0.7
      }
      pigment { Clear }
   }
   translate <0, -1, 0>
}

union {
   object { WoodSphere  translate <0, 9.5, 0> }
   object { Base }
   object { BrassBall translate < 10, -4.5,  10> }
   object { BrassBall translate < 10, -4.5, -10> }
   object { BrassBall translate <-10, -4.5,  10> }
   object { BrassBall translate <-10, -4.5, -10> }
   object { Railing translate <0, 3, 10> }
   object { Railing translate <0, 3, -10> }
   object { Railing rotate 90*y translate < 10, 3, 0> }
   object { Railing rotate 90*y translate <-10, 3, 0> }
}
