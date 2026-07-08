// Persistence Of Vision raytracer version 2.0 sample file.

// Bezier patch example
// by Alexander Enzmann


#include "shapes.inc"
#include "colors.inc"

bicubic_patch {
   type 1 flatness 0.1 u_steps 5 v_steps 5
   < 0.0, 0.0, 2.0>, < 1.0, 0.0, 0.0>, < 2.0, 0.0, 0.0>, < 3.0, 0.0, -2.0>,
   < 0.0, 1.0, 0.0>, < 1.0, 1.0, 0.0>, < 2.0, 1.0, 0.0>, < 3.0, 1.0,  0.0>,
   < 0.0, 2.0, 0.0>, < 1.0, 2.0, 0.0>, < 2.0, 2.0, 0.0>, < 3.0, 2.0,  0.0>,
   < 0.0, 3.0, 2.0>, < 1.0, 3.0  0.0>, < 2.0, 3.0, 0.0>, < 3.0, 3.0, -2.0>
   texture {
      pigment { checker color red 1.0 color blue 1.0 rotate 90*x }
      finish { phong 1 }
   }

   translate <-1.5, -1.5, 0>
   scale 2
   rotate <30, -70, 0>
}

// The viewer is eight units back along the z-axis. 
camera {
   location  <0.0,  0.0, -15.0>
   right     <4/3,  0.0,  0.0>
   up        <0.0,  1.0,  0.0>
   direction <0.0,  0.0,  1.0>
}

// Light source 
light_source { <100, 100, 0> colour White }
